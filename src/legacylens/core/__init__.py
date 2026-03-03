"""Core utilities for LegacyLens."""

from legacylens.core.config import Settings, get_settings
from legacylens.core.schemas import (
    CallSite,
    CallSitesResponse,
    Citation,
    Chunk,
    ChunkType,
    ChunkWithScore,
    Corpus,
    CorpusStatus,
    File,
    HealthResponse,
    ImpactReport,
    IngestProgress,
    IngestRequest,
    QueryRequest,
    QueryResponse,
    Reference,
    ReferenceKind,
    Span,
    Symbol,
    SymbolKind,
    SymbolResponse,
    UsageReference,
    UsageResponse,
)
from legacylens.core.spans import (
    clip_text_to_span,
    format_span_reference,
    merge_spans,
    spans_overlap,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Schemas
    "CallSite",
    "CallSitesResponse",
    "Citation",
    "Chunk",
    "ChunkType",
    "ChunkWithScore",
    "Corpus",
    "CorpusStatus",
    "File",
    "HealthResponse",
    "ImpactReport",
    "IngestProgress",
    "IngestRequest",
    "QueryRequest",
    "QueryResponse",
    "Reference",
    "ReferenceKind",
    "Span",
    "Symbol",
    "SymbolKind",
    "SymbolResponse",
    "UsageReference",
    "UsageResponse",
    # Spans
    "clip_text_to_span",
    "format_span_reference",
    "merge_spans",
    "spans_overlap",
]
