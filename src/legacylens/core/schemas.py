"""LegacyLens Pydantic schemas for API and internal use."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ChunkType(str, Enum):
    """Type of code chunk."""

    SUBROUTINE = "SUBROUTINE"
    FUNCTION = "FUNCTION"
    PROGRAM = "PROGRAM"
    MODULE = "MODULE"
    COMMON = "COMMON"
    WINDOW = "WINDOW"  # Fallback windowed chunk
    FILE = "FILE"  # Entire file


class SymbolKind(str, Enum):
    """Kind of symbol in the codebase."""

    SUBROUTINE = "SUBROUTINE"
    FUNCTION = "FUNCTION"
    PROGRAM = "PROGRAM"
    MODULE = "MODULE"
    COMMON = "COMMON"


class ReferenceKind(str, Enum):
    """Kind of reference between symbols."""

    CALL = "CALL"
    USE = "USE"
    INCLUDE = "INCLUDE"


class CorpusStatus(str, Enum):
    """Status of corpus ingestion."""

    PENDING = "PENDING"
    INGESTING = "INGESTING"
    READY = "READY"
    FAILED = "FAILED"


# === Span and Location ===


class Span(BaseModel):
    """Represents a location in source code."""

    file_path: str = Field(..., description="Relative path to the file")
    start_line: int = Field(..., ge=1, description="Starting line number (1-indexed)")
    end_line: int = Field(..., ge=1, description="Ending line number (1-indexed)")

    @property
    def line_count(self) -> int:
        """Number of lines in this span."""
        return self.end_line - self.start_line + 1

    def __str__(self) -> str:
        return f"{self.file_path}:{self.start_line}-{self.end_line}"


# === Chunk Models ===


class Chunk(BaseModel):
    """A retrievable chunk of code."""

    id: int | None = None
    file_id: int
    chunk_type: ChunkType
    name: str | None = None  # Subroutine/function/module name
    span: Span
    text: str
    token_count: int
    hash: str


class ChunkWithScore(Chunk):
    """A chunk with a relevance score from retrieval."""

    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")


# === Corpus and File Models ===


class Corpus(BaseModel):
    """A corpus (repository snapshot) in the system."""

    id: int | None = None
    repo_url: str
    commit_sha: str
    created_at: datetime | None = None
    status: CorpusStatus = CorpusStatus.PENDING


class File(BaseModel):
    """A file in the corpus."""

    id: int | None = None
    corpus_id: int
    path: str
    language: str = "fortran"
    encoding: str = "utf-8"
    line_count: int
    hash: str


# === Symbol and Reference Models ===


class Symbol(BaseModel):
    """A symbol (subroutine, function, etc.) in the codebase."""

    id: int | None = None
    corpus_id: int
    name: str
    kind: SymbolKind
    file_id: int
    span: Span
    signature: str | None = None


class Reference(BaseModel):
    """A reference from one symbol to another."""

    id: int | None = None
    from_symbol_id: int
    to_symbol_id: int | None = None  # None if symbol not found
    to_name: str  # Name of referenced symbol
    kind: ReferenceKind
    file_id: int
    line: int
    snippet: str | None = None


# === API Request/Response Models ===


class QueryRequest(BaseModel):
    """Request for a natural language query."""

    query: str = Field(..., min_length=1, max_length=1000)
    corpus_id: int | None = None
    top_k: int = Field(10, ge=1, le=50)


class Citation(BaseModel):
    """A citation to source code in an answer."""

    span: Span
    snippet: str = Field(..., max_length=500)
    relevance: str | None = None  # Why this citation is relevant


class QueryResponse(BaseModel):
    """Response to a natural language query."""

    query: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    chunks: list[ChunkWithScore] = Field(default_factory=list)
    latency_ms: float


class SymbolResponse(BaseModel):
    """Response for symbol lookup."""

    symbol: Symbol
    explanation: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class CallSite(BaseModel):
    """A call site for a subroutine/function."""

    caller_name: str
    caller_span: Span
    callee_name: str
    snippet: str


class CallSitesResponse(BaseModel):
    """Response for call site lookup."""

    symbol_name: str
    call_sites: list[CallSite]


class UsageReference(BaseModel):
    """A usage reference (INCLUDE/USE)."""

    from_file: str
    from_line: int
    kind: ReferenceKind
    to_name: str
    snippet: str


class UsageResponse(BaseModel):
    """Response for usage lookup."""

    symbol_name: str
    references: list[UsageReference]


class ImpactReport(BaseModel):
    """Impact analysis report for a symbol."""

    symbol_name: str
    direct_callers: list[str]
    indirect_callers: list[str]
    files_affected: list[str]
    estimated_blast_radius: str  # "low", "medium", "high"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.1.0"
    database: str = "connected"
    embedding_service: str = "available"


# === Ingestion Models ===


class IngestRequest(BaseModel):
    """Request to ingest a corpus."""

    repo_url: str
    tag: str | None = None
    commit_sha: str | None = None


class IngestProgress(BaseModel):
    """Progress report for ingestion."""

    corpus_id: int
    status: CorpusStatus
    files_total: int = 0
    files_processed: int = 0
    chunks_created: int = 0
    embeddings_created: int = 0
    errors: list[str] = Field(default_factory=list)
