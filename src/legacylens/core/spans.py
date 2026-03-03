"""Span utilities for working with source code locations."""

from typing import Iterable

from legacylens.core.schemas import Span


def spans_overlap(a: Span, b: Span) -> bool:
    """Check if two spans in the same file overlap."""
    if a.file_path != b.file_path:
        return False
    return a.start_line <= b.end_line and b.start_line <= a.end_line


def merge_spans(spans: Iterable[Span]) -> list[Span]:
    """Merge overlapping spans in the same file.

    Returns a list of non-overlapping spans sorted by file and line.
    """
    # Group by file
    by_file: dict[str, list[Span]] = {}
    for span in spans:
        if span.file_path not in by_file:
            by_file[span.file_path] = []
        by_file[span.file_path].append(span)

    merged = []
    for file_path, file_spans in by_file.items():
        # Sort by start line
        sorted_spans = sorted(file_spans, key=lambda s: s.start_line)

        if not sorted_spans:
            continue

        # Merge overlapping spans
        current = sorted_spans[0]
        for next_span in sorted_spans[1:]:
            if next_span.start_line <= current.end_line + 1:
                # Overlapping or adjacent, merge
                current = Span(
                    file_path=current.file_path,
                    start_line=current.start_line,
                    end_line=max(current.end_line, next_span.end_line),
                )
            else:
                merged.append(current)
                current = next_span
        merged.append(current)

    return sorted(merged, key=lambda s: (s.file_path, s.start_line))


def clip_text_to_span(text: str, span: Span, max_lines: int = 50) -> str:
    """Clip text to fit within a span, respecting line boundaries.

    If the text has more lines than max_lines, returns a clipped version.
    """
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text

    # Take first half and last half
    half = max_lines // 2
    first = lines[:half]
    last = lines[-(max_lines - half) :]

    return "\n".join([*first, f"... ({len(lines) - max_lines} lines omitted) ...", *last])


def format_span_reference(span: Span, snippet: str | None = None) -> str:
    """Format a span as a human-readable reference."""
    ref = f"{span.file_path}:{span.start_line}"
    if span.end_line != span.start_line:
        ref += f"-{span.end_line}"
    if snippet:
        # Take first line of snippet
        first_line = snippet.split("\n")[0][:60]
        ref += f" - {first_line}"
    return ref
