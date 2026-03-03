"""Main chunker module that combines Fortran parsing with fallback windowing."""

import hashlib
from pathlib import Path

from legacylens.chunking.fallback import FallbackChunker
from legacylens.chunking.fortran_parser import FortranParser, ParsedUnit, compute_hash
from legacylens.core.schemas import Chunk, ChunkType, Span


class ChunkerResult:
    """Result of chunking a file."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.chunks: list[Chunk] = []
        self.common_blocks: list[ParsedUnit] = []
        self.includes: list[tuple[int, str]] = []
        self.calls: list[tuple[int, str, str | None]] = []
        self.coverage_pct: float = 0.0
        self.total_lines: int = 0
        self.chunked_lines: int = 0

    def add_chunk(self, chunk: Chunk) -> None:
        """Add a chunk to the result."""
        self.chunks.append(chunk)
        self.chunked_lines += chunk.span.line_count

    def compute_coverage(self) -> None:
        """Compute coverage percentage."""
        if self.total_lines > 0:
            # Calculate unique lines covered
            covered = set()
            for chunk in self.chunks:
                for line in range(chunk.span.start_line, chunk.span.end_line + 1):
                    covered.add(line)
            self.chunked_lines = len(covered)
            self.coverage_pct = (self.chunked_lines / self.total_lines) * 100


class FortranChunker:
    """Main chunker for Fortran source files.

    Combines structural parsing with fallback windowing to achieve
    high coverage of legacy Fortran code.
    """

    def __init__(
        self,
        target_lines: int = 40,
        max_lines: int = 100,
        min_lines: int = 5,
        fallback_window: int = 50,
        fallback_overlap: int = 10,
    ):
        """Initialize the chunker.

        Args:
            target_lines: Target lines per chunk
            max_lines: Maximum lines before splitting
            min_lines: Minimum lines for a chunk
            fallback_window: Window size for fallback chunking
            fallback_overlap: Overlap for fallback windows
        """
        self.parser = FortranParser(target_lines, max_lines, min_lines)
        self.fallback = FallbackChunker(fallback_window, fallback_overlap)
        self.target_lines = target_lines
        self.max_lines = max_lines
        self.min_lines = min_lines

    def chunk_file(self, filepath: Path, file_id: int = 0) -> ChunkerResult:
        """Chunk a Fortran file.

        Args:
            filepath: Path to the Fortran source file
            file_id: Database ID for the file (for chunk creation)

        Returns:
            ChunkerResult with chunks, symbols, and metadata
        """
        result = ChunkerResult(filepath)

        # Read file
        try:
            text, encoding = self.parser._read_file(filepath)
        except Exception as e:
            result.coverage_pct = 0.0
            return result

        lines = text.split("\n")
        result.total_lines = len(lines)

        # Parse structural units
        units, common_blocks = self.parser.parse_file(filepath)
        result.common_blocks = common_blocks

        # Extract includes and calls
        result.includes = self.parser.extract_includes(lines)
        result.calls = self.parser.extract_calls(lines)

        # Convert units to chunks
        covered_ranges = []
        for unit in units:
            chunk = self._unit_to_chunk(unit, file_id, str(filepath))
            result.add_chunk(chunk)
            covered_ranges.append((unit.start_line, unit.end_line))

        # Add fallback chunks for uncovered lines
        fallback_chunks = self.fallback.chunk_uncovered_lines(lines, covered_ranges)
        for start_line, end_line, chunk_text in fallback_chunks:
            chunk = Chunk(
                file_id=file_id,
                chunk_type=ChunkType.WINDOW,
                name=None,
                span=Span(
                    file_path=str(filepath),
                    start_line=start_line,
                    end_line=end_line,
                ),
                text=chunk_text,
                token_count=self._estimate_tokens(chunk_text),
                hash=compute_hash(chunk_text),
            )
            result.add_chunk(chunk)

        result.compute_coverage()
        return result

    def _unit_to_chunk(
        self,
        unit: ParsedUnit,
        file_id: int,
        filepath: str,
    ) -> Chunk:
        """Convert a parsed unit to a Chunk."""
        return Chunk(
            file_id=file_id,
            chunk_type=unit.chunk_type,
            name=unit.name,
            span=Span(
                file_path=filepath,
                start_line=unit.start_line,
                end_line=unit.end_line,
            ),
            text=unit.text,
            token_count=self._estimate_tokens(unit.text),
            hash=compute_hash(unit.text),
        )

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses a simple heuristic: ~4 characters per token for code.
        For accurate counts, use tiktoken.
        """
        return len(text) // 4

    def chunk_directory(
        self,
        dirpath: Path,
        extensions: list[str] | None = None,
        file_id_start: int = 0,
    ) -> list[ChunkerResult]:
        """Chunk all Fortran files in a directory.

        Args:
            dirpath: Path to directory
            extensions: File extensions to process (default: .f, .f90, .f77)
            file_id_start: Starting file_id for chunks

        Returns:
            List of ChunkerResults for each file
        """
        if extensions is None:
            extensions = [".f", ".f90", ".f77", ".for"]

        results = []
        file_id = file_id_start

        for ext in extensions:
            for filepath in dirpath.rglob(f"*{ext}"):
                result = self.chunk_file(filepath, file_id)
                results.append(result)
                file_id += 1

        return results

    def get_coverage_report(self, results: list[ChunkerResult]) -> dict:
        """Generate a coverage report for chunking results.

        Args:
            results: List of ChunkerResults

        Returns:
            Dictionary with coverage statistics
        """
        total_lines = sum(r.total_lines for r in results)
        chunked_lines = sum(r.chunked_lines for r in results)
        total_chunks = sum(len(r.chunks) for r in results)
        total_files = len(results)

        by_type: dict[ChunkType, int] = {}
        for result in results:
            for chunk in result.chunks:
                by_type[chunk.chunk_type] = by_type.get(chunk.chunk_type, 0) + 1

        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "chunked_lines": chunked_lines,
            "coverage_pct": (chunked_lines / total_lines * 100) if total_lines > 0 else 0,
            "total_chunks": total_chunks,
            "chunks_by_type": {t.value: c for t, c in by_type.items()},
            "files_below_threshold": [
                str(r.filepath)
                for r in results
                if r.coverage_pct < 80.0
            ],
        }
