"""Unit tests for Fortran chunking."""

import pytest

from legacylens.chunking.chunker import ChunkerResult, FortranChunker
from legacylens.chunking.fortran_parser import FortranParser, ParsedUnit
from legacylens.core.schemas import ChunkType


class TestFortranParser:
    """Tests for the FortranParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = FortranParser()

    def test_parse_simple_subroutine(self, tmp_path):
        """Test parsing a simple SUBROUTINE."""
        fortran_file = tmp_path / "test.f"
        fortran_file.write_text(
            """
      SUBROUTINE CALC_HAZARD(X, Y, Z)
C     This is a comment
      REAL X, Y, Z
      Z = X + Y
      END SUBROUTINE
"""
        )

        units, commons = self.parser.parse_file(fortran_file)

        assert len(units) == 1
        assert units[0].name == "CALC_HAZARD"
        assert units[0].chunk_type == ChunkType.SUBROUTINE
        assert units[0].start_line == 2
        assert units[0].end_line == 6

    def test_parse_function(self, tmp_path):
        """Test parsing a FUNCTION."""
        fortran_file = tmp_path / "test.f"
        fortran_file.write_text(
            """
      FUNCTION ADD(A, B)
      REAL ADD
      ADD = A + B
      RETURN
      END
"""
        )

        units, commons = self.parser.parse_file(fortran_file)

        assert len(units) == 1
        assert units[0].name == "ADD"
        assert units[0].chunk_type == ChunkType.FUNCTION

    def test_parse_program(self, tmp_path):
        """Test parsing a PROGRAM."""
        fortran_file = tmp_path / "test.f"
        fortran_file.write_text(
            """
      PROGRAM MAIN
      PRINT *, 'Hello World'
      END PROGRAM
"""
        )

        units, commons = self.parser.parse_file(fortran_file)

        assert len(units) == 1
        assert units[0].name == "MAIN"
        assert units[0].chunk_type == ChunkType.PROGRAM

    def test_parse_multiple_subroutines(self, tmp_path):
        """Test parsing multiple SUBROUTINEs in one file."""
        fortran_file = tmp_path / "test.f"
        fortran_file.write_text(
            """
      SUBROUTINE FIRST()
      END SUBROUTINE

      SUBROUTINE SECOND()
      END SUBROUTINE

      SUBROUTINE THIRD()
      END SUBROUTINE
"""
        )

        units, commons = self.parser.parse_file(fortran_file)

        assert len(units) == 3
        assert units[0].name == "FIRST"
        assert units[1].name == "SECOND"
        assert units[2].name == "THIRD"

    def test_extract_common_blocks(self, tmp_path):
        """Test extraction of COMMON blocks."""
        fortran_file = tmp_path / "test.f"
        fortran_file.write_text(
            """
      SUBROUTINE TEST()
      COMMON /PARAMS/ A, B, C
      COMMON /STATE/ X, Y
      END SUBROUTINE
"""
        )

        units, commons = self.parser.parse_file(fortran_file)

        assert len(commons) == 2
        assert commons[0].name == "COMMON/PARAMS"
        assert commons[1].name == "COMMON/STATE"

    def test_extract_includes(self, tmp_path):
        """Test extraction of INCLUDE statements."""
        fortran_file = tmp_path / "test.f"
        fortran_file.write_text(
            """
      SUBROUTINE TEST()
      INCLUDE 'params.inc'
      INCLUDE 'consts.inc'
      END SUBROUTINE
"""
        )

        text, _ = self.parser._read_file(fortran_file)
        lines = text.split("\n")
        includes = self.parser.extract_includes(lines)

        assert len(includes) == 2
        assert includes[0][1] == "params.inc"
        assert includes[1][1] == "consts.inc"

    def test_extract_calls(self, tmp_path):
        """Test extraction of CALL statements."""
        fortran_file = tmp_path / "test.f"
        fortran_file.write_text(
            """
      SUBROUTINE MAIN()
      CALL SUB1()
      CALL SUB2(X, Y)
      END SUBROUTINE
"""
        )

        text, _ = self.parser._read_file(fortran_file)
        lines = text.split("\n")
        calls = self.parser.extract_calls(lines)

        assert len(calls) == 2
        assert calls[0][1] == "SUB1"
        assert calls[1][1] == "SUB2"

    def test_case_insensitive(self, tmp_path):
        """Test that parsing is case-insensitive."""
        fortran_file = tmp_path / "test.f"
        fortran_file.write_text(
            """
      subroutine LowerCase(a, b)
      end subroutine
"""
        )

        units, commons = self.parser.parse_file(fortran_file)

        assert len(units) == 1
        assert units[0].name.upper() == "LOWERCASE"

    def test_f77_plain_end(self, tmp_path):
        """Test F77 style with plain END statement."""
        fortran_file = tmp_path / "test.f"
        fortran_file.write_text(
            """
      SUBROUTINE OLDSTYLE()
      RETURN
      END
"""
        )

        units, commons = self.parser.parse_file(fortran_file)

        assert len(units) == 1
        assert units[0].name == "OLDSTYLE"


class TestFortranChunker:
    """Tests for the FortranChunker class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chunker = FortranChunker()

    def test_chunk_simple_file(self, tmp_path):
        """Test chunking a simple file."""
        fortran_file = tmp_path / "test.f"
        fortran_file.write_text(
            """
      SUBROUTINE CALC(A, B)
      REAL A, B
      B = A * 2
      END SUBROUTINE
"""
        )

        result = self.chunker.chunk_file(fortran_file)

        assert len(result.chunks) >= 1
        assert result.coverage_pct > 0

    def test_chunk_file_with_fallback(self, tmp_path):
        """Test that fallback chunking covers unparsed sections."""
        fortran_file = tmp_path / "test.f"
        # File with code outside subroutines
        fortran_file.write_text(
            """
C     Header comment
C     More comments

      PROGRAM MAIN
      CALL INIT()
      END PROGRAM

C     Some declaration outside any unit
      PARAMETER (PI=3.14159)
"""
        )

        result = self.chunker.chunk_file(fortran_file)

        # Should have chunks and reasonable coverage
        assert len(result.chunks) >= 1
        # Coverage may not be 100% due to comments
        assert result.coverage_pct >= 50.0

    def test_coverage_report(self, tmp_path):
        """Test coverage report generation."""
        for file_num in range(3):
            fortran_file = tmp_path / f"test{file_num}.f"
            fortran_file.write_text(
                f"""
      SUBROUTINE TEST{file_num}()
      END SUBROUTINE
"""
            )

        results = self.chunker.chunk_directory(tmp_path)
        report = self.chunker.get_coverage_report(results)

        assert report["total_files"] == 3
        assert report["total_chunks"] >= 3
        assert report["coverage_pct"] > 0

    def test_chunk_has_correct_spans(self, tmp_path):
        """Test that chunks have correct span information."""
        fortran_file = tmp_path / "test.f"
        fortran_file.write_text(
            """
      SUBROUTINE CALC()
      END SUBROUTINE
"""
        )

        result = self.chunker.chunk_file(fortran_file)

        assert len(result.chunks) >= 1
        chunk = result.chunks[0]
        assert chunk.span.start_line >= 1
        assert chunk.span.end_line >= chunk.span.start_line
        assert str(fortran_file) in chunk.span.file_path


class TestFallbackChunker:
    """Tests for the fallback windowed chunking."""

    def test_windowed_chunks_basic(self):
        """Test basic windowed chunking."""
        from legacylens.chunking.fallback import windowed_chunks

        lines = [f"Line {i}" for i in range(100)]
        chunks = windowed_chunks(lines, window_size=50, overlap=10)

        assert len(chunks) >= 2
        # First chunk should start at line 1
        assert chunks[0][0] == 1
        # Chunks should overlap
        assert chunks[0][2] > 0  # Has text

    def test_small_file_handling(self):
        """Test handling of files smaller than window size."""
        from legacylens.chunking.fallback import windowed_chunks

        lines = [f"Line {i}" for i in range(10)]
        chunks = windowed_chunks(lines, window_size=50, overlap=10)

        assert len(chunks) == 1
        assert chunks[0][0] == 1
        assert chunks[0][1] == 10
