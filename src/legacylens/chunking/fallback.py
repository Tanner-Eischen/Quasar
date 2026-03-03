"""Fallback window-based chunker for unparseable code sections."""

from legacylens.core.schemas import ChunkType, Span


def windowed_chunks(
    lines: list[str],
    window_size: int = 50,
    overlap: int = 10,
) -> list[tuple[int, int, str]]:
    """Create overlapping windowed chunks from lines.

    Args:
        lines: List of source code lines
        window_size: Number of lines per window
        overlap: Number of overlapping lines between windows

    Returns:
        List of (start_line, end_line, text) tuples
    """
    if not lines:
        return []

    chunks = []
    start = 0
    step = window_size - overlap

    while start < len(lines):
        end = min(start + window_size, len(lines))
        chunk_lines = lines[start:end]
        text = "\n".join(chunk_lines)
        chunks.append((start + 1, end, text))  # 1-indexed

        if end >= len(lines):
            break
        start += step

    return chunks


class FallbackChunker:
    """Window-based chunker for code that can't be parsed structurally."""

    def __init__(
        self,
        window_lines: int = 50,
        overlap_lines: int = 10,
    ):
        """Initialize the fallback chunker.

        Args:
            window_lines: Number of lines per window
            overlap_lines: Overlap between consecutive windows
        """
        self.window_lines = window_lines
        self.overlap_lines = overlap_lines

    def chunk_uncovered_lines(
        self,
        lines: list[str],
        covered_ranges: list[tuple[int, int]],
    ) -> list[tuple[int, int, str]]:
        """Chunk lines that aren't covered by existing ranges.

        Args:
            lines: All source lines
            covered_ranges: List of (start, end) tuples already covered (1-indexed)

        Returns:
            List of (start_line, end_line, text) tuples for uncovered sections
        """
        if not lines:
            return []

        # Mark covered lines
        covered = set()
        for start, end in covered_ranges:
            for i in range(start, end + 1):
                if 1 <= i <= len(lines):
                    covered.add(i - 1)  # Convert to 0-indexed

        # Find uncovered ranges
        chunks = []
        current_start = None

        for i in range(len(lines)):
            if i not in covered:
                if current_start is None:
                    current_start = i
            else:
                if current_start is not None:
                    # End uncovered section
                    uncovered_lines = lines[current_start:i]
                    if len(uncovered_lines) >= 5:  # Minimum chunk size
                        chunks.extend(
                            windowed_chunks(
                                uncovered_lines,
                                self.window_lines,
                                self.overlap_lines,
                            )
                        )
                    current_start = None

        # Handle trailing uncovered lines
        if current_start is not None:
            uncovered_lines = lines[current_start:]
            if len(uncovered_lines) >= 5:
                chunks.extend(
                    windowed_chunks(
                        uncovered_lines,
                        self.window_lines,
                        self.overlap_lines,
                    )
                )

        return chunks
