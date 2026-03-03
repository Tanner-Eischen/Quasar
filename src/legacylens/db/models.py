"""SQLAlchemy database models for LegacyLens."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from legacylens.core.schemas import ChunkType, CorpusStatus, ReferenceKind, SymbolKind


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class CorpusModel(Base):
    """Corpus (repository snapshot) model."""

    __tablename__ = "corpus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[CorpusStatus] = mapped_column(
        Enum(CorpusStatus),
        default=CorpusStatus.PENDING,
        nullable=False,
    )

    # Relationships
    files: Mapped[list["FileModel"]] = relationship(back_populates="corpus", cascade="all, delete-orphan")
    symbols: Mapped[list["SymbolModel"]] = relationship(back_populates="corpus", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"CorpusModel(id={self.id}, repo_url='{self.repo_url}', commit_sha='{self.commit_sha[:8]}')"


class FileModel(Base):
    """File in corpus model."""

    __tablename__ = "file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    corpus_id: Mapped[int] = mapped_column(ForeignKey("corpus.id"), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    language: Mapped[str] = mapped_column(String(50), default="fortran", nullable=False)
    encoding: Mapped[str] = mapped_column(String(20), default="utf-8", nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationships
    corpus: Mapped["CorpusModel"] = relationship(back_populates="files")
    chunks: Mapped[list["ChunkModel"]] = relationship(back_populates="file", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_file_corpus_path", "corpus_id", "path", unique=True),)

    def __repr__(self) -> str:
        return f"FileModel(id={self.id}, path='{self.path}')"


class ChunkModel(Base):
    """Chunk of code model."""

    __tablename__ = "chunk"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("file.id"), nullable=False)
    chunk_type: Mapped[ChunkType] = mapped_column(Enum(ChunkType), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationships
    file: Mapped["FileModel"] = relationship(back_populates="chunks")
    embedding: Mapped["EmbeddingModel | None"] = relationship(
        back_populates="chunk",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_chunk_file_lines", "file_id", "start_line", "end_line"),)

    def __repr__(self) -> str:
        return f"ChunkModel(id={self.id}, type={self.chunk_type}, name='{self.name}')"


class EmbeddingModel(Base):
    """Embedding vector model."""

    __tablename__ = "embedding"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("chunk.id"), unique=True, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    dims: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    # Relationships
    chunk: Mapped["ChunkModel"] = relationship(back_populates="embedding")

    def __repr__(self) -> str:
        return f"EmbeddingModel(id={self.id}, chunk_id={self.chunk_id}, dims={self.dims})"


class SymbolModel(Base):
    """Symbol (subroutine, function, etc.) model."""

    __tablename__ = "symbol"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    corpus_id: Mapped[int] = mapped_column(ForeignKey("corpus.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[SymbolKind] = mapped_column(Enum(SymbolKind), nullable=False)
    file_id: Mapped[int] = mapped_column(ForeignKey("file.id"), nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    corpus: Mapped["CorpusModel"] = relationship(back_populates="symbols")
    outgoing_refs: Mapped[list["ReferenceModel"]] = relationship(
        "ReferenceModel",
        foreign_keys="ReferenceModel.from_symbol_id",
        back_populates="from_symbol",
        cascade="all, delete-orphan",
    )
    incoming_refs: Mapped[list["ReferenceModel"]] = relationship(
        "ReferenceModel",
        foreign_keys="ReferenceModel.to_symbol_id",
        back_populates="to_symbol",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_symbol_corpus_name", "corpus_id", "name"),
        Index("ix_symbol_corpus_kind", "corpus_id", "kind"),
    )

    def __repr__(self) -> str:
        return f"SymbolModel(id={self.id}, name='{self.name}', kind={self.kind})"


class ReferenceModel(Base):
    """Reference between symbols model."""

    __tablename__ = "reference"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_symbol_id: Mapped[int] = mapped_column(ForeignKey("symbol.id"), nullable=False)
    to_symbol_id: Mapped[int | None] = mapped_column(ForeignKey("symbol.id"), nullable=True)
    to_name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[ReferenceKind] = mapped_column(Enum(ReferenceKind), nullable=False)
    file_id: Mapped[int] = mapped_column(ForeignKey("file.id"), nullable=False)
    line: Mapped[int] = mapped_column(Integer, nullable=False)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    from_symbol: Mapped["SymbolModel"] = relationship(
        foreign_keys=[from_symbol_id],
        back_populates="outgoing_refs",
    )
    to_symbol: Mapped["SymbolModel | None"] = relationship(
        foreign_keys=[to_symbol_id],
        back_populates="incoming_refs",
    )

    __table_args__ = (Index("ix_reference_to_name", "to_name"),)

    def __repr__(self) -> str:
        return f"ReferenceModel(id={self.id}, kind={self.kind}, to_name='{self.to_name}')"


class QueryLogModel(Base):
    """Query log for metrics and debugging."""

    __tablename__ = "query_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    corpus_id: Mapped[int | None] = mapped_column(ForeignKey("corpus.id"), nullable=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    chunks_retrieved: Mapped[int] = mapped_column(Integer, default=0)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"QueryLogModel(id={self.id}, query='{self.query[:50]}...')"
