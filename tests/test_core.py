"""Unit tests for core schemas and utilities."""

import pytest

from legacylens.core.schemas import Chunk, ChunkType, Span
from legacylens.core.spans import merge_spans, spans_overlap


class TestSpan:
    """Tests for the Span class."""

    def test_span_creation(self):
        """Test creating a span."""
        span = Span(file_path="src/test.f", start_line=10, end_line=20)

        assert span.file_path == "src/test.f"
        assert span.start_line == 10
        assert span.end_line == 20
        assert span.line_count == 11

    def test_span_string_representation(self):
        """Test span string representation."""
        span = Span(file_path="src/test.f", start_line=10, end_line=20)

        assert str(span) == "src/test.f:10-20"

    def test_single_line_span(self):
        """Test single-line span."""
        span = Span(file_path="src/test.f", start_line=5, end_line=5)

        assert span.line_count == 1
        assert str(span) == "src/test.f:5-5"


class TestSpanUtilities:
    """Tests for span utility functions."""

    def test_spans_overlap_true(self):
        """Test overlapping spans detection."""
        a = Span(file_path="test.f", start_line=10, end_line=20)
        b = Span(file_path="test.f", start_line=15, end_line=25)

        assert spans_overlap(a, b) is True
        assert spans_overlap(b, a) is True

    def test_spans_overlap_false(self):
        """Test non-overlapping spans detection."""
        a = Span(file_path="test.f", start_line=10, end_line=20)
        b = Span(file_path="test.f", start_line=21, end_line=30)

        assert spans_overlap(a, b) is False

    def test_spans_different_files(self):
        """Test spans in different files."""
        a = Span(file_path="test1.f", start_line=10, end_line=20)
        b = Span(file_path="test2.f", start_line=10, end_line=20)

        assert spans_overlap(a, b) is False

    def test_merge_spans(self):
        """Test merging overlapping spans."""
        spans = [
            Span(file_path="test.f", start_line=10, end_line=20),
            Span(file_path="test.f", start_line=15, end_line=25),
            Span(file_path="test.f", start_line=30, end_line=40),
        ]

        merged = merge_spans(spans)

        assert len(merged) == 2
        assert merged[0].start_line == 10
        assert merged[0].end_line == 25
        assert merged[1].start_line == 30
        assert merged[1].end_line == 40


class TestChunk:
    """Tests for the Chunk class."""

    def test_chunk_creation(self):
        """Test creating a chunk."""
        span = Span(file_path="test.f", start_line=1, end_line=10)
        chunk = Chunk(
            id=1,
            file_id=1,
            chunk_type=ChunkType.SUBROUTINE,
            name="CALC_HAZARD",
            span=span,
            text="SUBROUTINE CALC_HAZARD\n...",
            token_count=50,
            hash="abc123",
        )

        assert chunk.id == 1
        assert chunk.chunk_type == ChunkType.SUBROUTINE
        assert chunk.name == "CALC_HAZARD"

    def test_chunk_type_enum(self):
        """Test ChunkType enum values."""
        assert ChunkType.SUBROUTINE.value == "SUBROUTINE"
        assert ChunkType.FUNCTION.value == "FUNCTION"
        assert ChunkType.PROGRAM.value == "PROGRAM"
        assert ChunkType.MODULE.value == "MODULE"
        assert ChunkType.WINDOW.value == "WINDOW"
