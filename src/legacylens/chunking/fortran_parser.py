"""Fortran-aware parser for chunking legacy code.

This module provides regex-based parsing for Fortran 77 fixed-format code,
with detection of SUBROUTINE, FUNCTION, PROGRAM, and MODULE boundaries.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from legacylens.core.schemas import ChunkType, Span


@dataclass
class ParsedUnit:
    """A parsed unit of Fortran code (subroutine, function, etc.)."""

    name: str
    chunk_type: ChunkType
    start_line: int
    end_line: int
    text: str
    signature: str | None = None


class FortranParser:
    """Parser for Fortran 77 fixed-format source code.

    Handles:
    - SUBROUTINE ... END SUBROUTINE (or END)
    - FUNCTION ... END FUNCTION (or END)
    - PROGRAM ... END PROGRAM (or END)
    - MODULE ... END MODULE (if F90+ sections exist)
    - COMMON blocks (extracted as symbols)
    - INCLUDE statements (tracked as references)

    Notes on Fortran 77 fixed-format:
    - Columns 1-5: statement label (optional)
    - Column 6: continuation character
    - Columns 7-72: statement
    - Column 1: C or * for comment
    """

    # Regex patterns for Fortran constructs
    # These are case-insensitive (re.IGNORECASE)

    # Subroutine: SUBROUTINE name [(args)]
    SUBROUTINE_START = re.compile(
        r"^\s*SUBROUTINE\s+(\w+)\s*(?:\((.*?)\))?\s*$",
        re.IGNORECASE,
    )
    SUBROUTINE_END = re.compile(
        r"^\s*END\s*(?:SUBROUTINE\s*(\w+)?)?\s*$",
        re.IGNORECASE,
    )

    # Function: [type] FUNCTION name [(args)]
    FUNCTION_START = re.compile(
        r"^\s*(?:(?:INTEGER|REAL|DOUBLE\s*PRECISION|LOGICAL|CHARACTER)\s*)?"
        r"FUNCTION\s+(\w+)\s*(?:\((.*?)\))?\s*$",
        re.IGNORECASE,
    )
    FUNCTION_END = re.compile(
        r"^\s*END\s*(?:FUNCTION\s*(\w+)?)?\s*$",
        re.IGNORECASE,
    )

    # Program: PROGRAM name
    PROGRAM_START = re.compile(
        r"^\s*PROGRAM\s+(\w+)\s*$",
        re.IGNORECASE,
    )
    PROGRAM_END = re.compile(
        r"^\s*END\s*(?:PROGRAM\s*(\w+)?)?\s*$",
        re.IGNORECASE,
    )

    # Module (F90+): MODULE name
    MODULE_START = re.compile(
        r"^\s*MODULE\s+(\w+)\s*$",
        re.IGNORECASE,
    )
    MODULE_END = re.compile(
        r"^\s*END\s*(?:MODULE\s*(\w+)?)?\s*$",
        re.IGNORECASE,
    )

    # Generic END statement (for F77 style)
    GENERIC_END = re.compile(
        r"^\s*END\s*$",
        re.IGNORECASE,
    )

    # COMMON block: COMMON /name/ var1, var2, ...
    COMMON_BLOCK = re.compile(
        r"^\s*COMMON\s*/(\w+)/\s*(.+?)\s*$",
        re.IGNORECASE,
    )

    # INCLUDE statement: INCLUDE 'filename'
    INCLUDE_STMT = re.compile(
        r"^\s*INCLUDE\s*['\"](.+?)['\"]\s*$",
        re.IGNORECASE,
    )

    # CALL statement: CALL name [(args)]
    CALL_STMT = re.compile(
        r"^\s*CALL\s+(\w+)\s*(?:\((.*?)\))?\s*$",
        re.IGNORECASE,
    )

    # Comment line (column 1 is C or *)
    COMMENT_LINE = re.compile(r"^[Cc\*]")

    # Continuation line (column 6 is non-blank)
    CONTINUATION = re.compile(r"^.{5}\S")

    def __init__(
        self,
        target_lines: int = 40,
        max_lines: int = 100,
        min_lines: int = 5,
    ):
        """Initialize the parser.

        Args:
            target_lines: Target lines per chunk
            max_lines: Maximum lines before splitting
            min_lines: Minimum lines (tiny units will be merged)
        """
        self.target_lines = target_lines
        self.max_lines = max_lines
        self.min_lines = min_lines

    def parse_file(self, filepath: Path) -> tuple[list[ParsedUnit], list[ParsedUnit]]:
        """Parse a Fortran file and extract code units.

        Args:
            filepath: Path to the Fortran source file

        Returns:
            Tuple of (code_units, common_blocks)
        """
        # Read file with encoding detection
        text, encoding = self._read_file(filepath)
        lines = text.split("\n")

        # Extract code units
        units = self._extract_units(lines, str(filepath))

        # Extract COMMON blocks as separate symbols
        common_blocks = self._extract_common_blocks(lines, str(filepath))

        return units, common_blocks

    def _read_file(self, filepath: Path) -> tuple[str, str]:
        """Read file with encoding detection.

        Tries common encodings for legacy Fortran files.
        """
        encodings = ["utf-8", "latin-1", "cp1252", "ascii"]

        for encoding in encodings:
            try:
                text = filepath.read_text(encoding=encoding)
                return text, encoding
            except UnicodeDecodeError:
                continue

        # Fallback: read with errors='replace'
        return filepath.read_text(encoding="utf-8", errors="replace"), "utf-8-replaced"

    def _extract_units(self, lines: list[str], filepath: str) -> list[ParsedUnit]:
        """Extract code units from lines.

        Uses a simple state machine to track nested constructs.
        """
        units = []
        current_unit: dict | None = None
        unit_stack: list[dict] = []

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or self.COMMENT_LINE.match(line):
                if current_unit:
                    current_unit["lines"].append(line)
                continue

            # Check for unit starts
            if match := self.SUBROUTINE_START.match(stripped):
                unit = self._start_unit("SUBROUTINE", match.group(1), line_num, match.group(2))
                if current_unit:
                    unit_stack.append(current_unit)
                current_unit = unit
                continue

            if match := self.FUNCTION_START.match(stripped):
                unit = self._start_unit("FUNCTION", match.group(1), line_num, match.group(2))
                if current_unit:
                    unit_stack.append(current_unit)
                current_unit = unit
                continue

            if match := self.PROGRAM_START.match(stripped):
                unit = self._start_unit("PROGRAM", match.group(1), line_num, None)
                if current_unit:
                    unit_stack.append(current_unit)
                current_unit = unit
                continue

            if match := self.MODULE_START.match(stripped):
                unit = self._start_unit("MODULE", match.group(1), line_num, None)
                if current_unit:
                    unit_stack.append(current_unit)
                current_unit = unit
                continue

            # Check for unit ends
            if current_unit:
                ended = self._check_end(stripped, current_unit)
                if ended:
                    current_unit["end_line"] = line_num
                    current_unit["lines"].append(line)
                    units.append(self._create_unit(current_unit))

                    # Pop from stack if nested
                    if unit_stack:
                        current_unit = unit_stack.pop()
                    else:
                        current_unit = None
                    continue
                else:
                    current_unit["lines"].append(line)

        # Handle unclosed units (append what we have)
        if current_unit:
            current_unit["end_line"] = len(lines)
            units.append(self._create_unit(current_unit))

        return units

    def _start_unit(
        self,
        unit_type: str,
        name: str,
        line_num: int,
        args: str | None,
    ) -> dict:
        """Start a new code unit."""
        return {
            "type": unit_type,
            "name": name,
            "start_line": line_num,
            "end_line": None,
            "lines": [],
            "signature": f"{unit_type} {name}({args})" if args else f"{unit_type} {name}",
        }

    def _check_end(self, stripped: str, current: dict) -> bool:
        """Check if this line ends the current unit."""
        unit_type = current["type"]
        name = current["name"]

        if unit_type == "SUBROUTINE":
            if match := self.SUBROUTINE_END.match(stripped):
                # Check if name matches (if specified)
                if match.group(1) and match.group(1).lower() != name.lower():
                    return False  # END SUBROUTINE for different routine
                return True
            # F77 style: plain END
            if self.GENERIC_END.match(stripped):
                return True

        elif unit_type == "FUNCTION":
            if match := self.FUNCTION_END.match(stripped):
                if match.group(1) and match.group(1).lower() != name.lower():
                    return False
                return True
            if self.GENERIC_END.match(stripped):
                return True

        elif unit_type == "PROGRAM":
            if match := self.PROGRAM_END.match(stripped):
                if match.group(1) and match.group(1).lower() != name.lower():
                    return False
                return True
            if self.GENERIC_END.match(stripped):
                return True

        elif unit_type == "MODULE":
            if match := self.MODULE_END.match(stripped):
                if match.group(1) and match.group(1).lower() != name.lower():
                    return False
                return True

        return False

    def _create_unit(self, unit_data: dict) -> ParsedUnit:
        """Create a ParsedUnit from unit data."""
        text = "\n".join(unit_data["lines"])
        return ParsedUnit(
            name=unit_data["name"],
            chunk_type=ChunkType(unit_data["type"]),
            start_line=unit_data["start_line"],
            end_line=unit_data["end_line"],
            text=text,
            signature=unit_data.get("signature"),
        )

    def _extract_common_blocks(self, lines: list[str], filepath: str) -> list[ParsedUnit]:
        """Extract COMMON block declarations as symbols."""
        common_blocks = []

        for line_num, line in enumerate(lines, start=1):
            if match := self.COMMON_BLOCK.match(line.strip()):
                name = match.group(1)
                variables = match.group(2)
                common_blocks.append(
                    ParsedUnit(
                        name=f"COMMON/{name}",
                        chunk_type=ChunkType.COMMON,
                        start_line=line_num,
                        end_line=line_num,
                        text=line.strip(),
                        signature=f"COMMON /{name}/ {variables}",
                    )
                )

        return common_blocks

    def extract_includes(self, lines: list[str]) -> list[tuple[int, str]]:
        """Extract INCLUDE statements.

        Returns:
            List of (line_number, include_path) tuples
        """
        includes = []
        for line_num, line in enumerate(lines, start=1):
            if match := self.INCLUDE_STMT.match(line.strip()):
                includes.append((line_num, match.group(1)))
        return includes

    def extract_calls(self, lines: list[str]) -> list[tuple[int, str, str | None]]:
        """Extract CALL statements.

        Returns:
            List of (line_number, subroutine_name, args) tuples
        """
        calls = []
        for line_num, line in enumerate(lines, start=1):
            if match := self.CALL_STMT.match(line.strip()):
                calls.append((line_num, match.group(1), match.group(2)))
        return calls


def compute_hash(text: str) -> str:
    """Compute SHA-256 hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
