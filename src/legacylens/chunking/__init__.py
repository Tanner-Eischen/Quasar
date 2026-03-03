"""Chunking module for Fortran source code."""

from legacylens.chunking.chunker import ChunkerResult, FortranChunker
from legacylens.chunking.fallback import FallbackChunker, windowed_chunks
from legacylens.chunking.fortran_parser import FortranParser, ParsedUnit, compute_hash

__all__ = [
    "ChunkerResult",
    "FallbackChunker",
    "FortranChunker",
    "FortranParser",
    "ParsedUnit",
    "compute_hash",
    "windowed_chunks",
]
