"""Data access layer with repository classes for LegacyLens.

Provides CRUD operations and vector search for corpus, files, chunks, and embeddings.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from legacylens.core.schemas import ChunkType, ChunkWithScore, CorpusStatus, ReferenceKind, Span, SymbolKind
from legacylens.db.models import (
    ChunkModel,
    CorpusModel,
    EmbeddingModel,
    FileModel,
    QueryLogModel,
    ReferenceModel,
    SymbolModel,
)


class CorpusRepository:
    """Repository for corpus operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        repo_url: str,
        commit_sha: str,
        status: CorpusStatus = CorpusStatus.PENDING,
    ) -> CorpusModel:
        """Create a new corpus record."""
        corpus = CorpusModel(
            repo_url=repo_url,
            commit_sha=commit_sha,
            status=status,
        )
        self.session.add(corpus)
        await self.session.flush()
        return corpus

    async def get_by_id(self, corpus_id: int) -> CorpusModel | None:
        """Get corpus by ID."""
        result = await self.session.execute(
            select(CorpusModel).where(CorpusModel.id == corpus_id)
        )
        return result.scalar_one_or_none()

    async def get_ready_corpus(self) -> CorpusModel | None:
        """Get the most recent READY corpus."""
        result = await self.session.execute(
            select(CorpusModel)
            .where(CorpusModel.status == CorpusStatus.READY)
            .order_by(CorpusModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_corpus(self) -> CorpusModel | None:
        """Get the most recent corpus regardless of status."""
        result = await self.session.execute(
            select(CorpusModel).order_by(CorpusModel.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self, corpus_id: int, status: CorpusStatus
    ) -> CorpusModel | None:
        """Update corpus status."""
        corpus = await self.get_by_id(corpus_id)
        if corpus:
            corpus.status = status
            await self.session.flush()
        return corpus

    async def list_all(self, limit: int = 100) -> list[CorpusModel]:
        """List all corpora."""
        result = await self.session.execute(
            select(CorpusModel).order_by(CorpusModel.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


class FileRepository:
    """Repository for file operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        corpus_id: int,
        path: str,
        line_count: int,
        hash: str,
        language: str = "fortran",
        encoding: str = "utf-8",
    ) -> FileModel:
        """Create a new file record."""
        file = FileModel(
            corpus_id=corpus_id,
            path=path,
            language=language,
            encoding=encoding,
            line_count=line_count,
            hash=hash,
        )
        self.session.add(file)
        await self.session.flush()
        return file

    async def get_by_id(self, file_id: int) -> FileModel | None:
        """Get file by ID."""
        result = await self.session.execute(
            select(FileModel).where(FileModel.id == file_id)
        )
        return result.scalar_one_or_none()

    async def get_by_path(self, corpus_id: int, path: str) -> FileModel | None:
        """Get file by corpus and path."""
        result = await self.session.execute(
            select(FileModel).where(
                FileModel.corpus_id == corpus_id,
                FileModel.path == path,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_corpus(self, corpus_id: int) -> list[FileModel]:
        """List all files in a corpus."""
        result = await self.session.execute(
            select(FileModel)
            .where(FileModel.corpus_id == corpus_id)
            .order_by(FileModel.path)
        )
        return list(result.scalars().all())

    async def count_by_corpus(self, corpus_id: int) -> int:
        """Count files in a corpus."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(FileModel.id)).where(FileModel.corpus_id == corpus_id)
        )
        return result.scalar() or 0


class ChunkRepository:
    """Repository for chunk operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        file_id: int,
        chunk_type: ChunkType,
        start_line: int,
        end_line: int,
        text: str,
        token_count: int,
        hash: str,
        name: str | None = None,
    ) -> ChunkModel:
        """Create a new chunk record."""
        chunk = ChunkModel(
            file_id=file_id,
            chunk_type=chunk_type,
            name=name,
            start_line=start_line,
            end_line=end_line,
            text=text,
            token_count=token_count,
            hash=hash,
        )
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def batch_create(self, chunks: list[dict[str, Any]]) -> list[ChunkModel]:
        """Create multiple chunks at once."""
        models = []
        for chunk_data in chunks:
            chunk = ChunkModel(**chunk_data)
            self.session.add(chunk)
            models.append(chunk)
        await self.session.flush()
        return models

    async def get_by_id(self, chunk_id: int) -> ChunkModel | None:
        """Get chunk by ID with file relationship."""
        result = await self.session.execute(
            select(ChunkModel)
            .options(selectinload(ChunkModel.file))
            .where(ChunkModel.id == chunk_id)
        )
        return result.scalar_one_or_none()

    async def list_by_file(self, file_id: int) -> list[ChunkModel]:
        """List all chunks in a file."""
        result = await self.session.execute(
            select(ChunkModel)
            .where(ChunkModel.file_id == file_id)
            .order_by(ChunkModel.start_line)
        )
        return list(result.scalars().all())

    async def list_by_corpus(self, corpus_id: int) -> list[ChunkModel]:
        """List all chunks in a corpus."""
        result = await self.session.execute(
            select(ChunkModel)
            .join(FileModel)
            .where(FileModel.corpus_id == corpus_id)
            .order_by(FileModel.path, ChunkModel.start_line)
        )
        return list(result.scalars().all())

    async def count_by_corpus(self, corpus_id: int) -> int:
        """Count chunks in a corpus."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(ChunkModel.id))
            .join(FileModel)
            .where(FileModel.corpus_id == corpus_id)
        )
        return result.scalar() or 0


class EmbeddingRepository:
    """Repository for embedding operations with vector search."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        chunk_id: int,
        model: str,
        dims: int,
        vector: list[float],
    ) -> EmbeddingModel:
        """Create a new embedding record."""
        embedding = EmbeddingModel(
            chunk_id=chunk_id,
            model=model,
            dims=dims,
            vector=vector,
        )
        self.session.add(embedding)
        await self.session.flush()
        return embedding

    async def batch_create(
        self, embeddings: list[dict[str, Any]]
    ) -> list[EmbeddingModel]:
        """Create multiple embeddings at once."""
        models = []
        for emb_data in embeddings:
            embedding = EmbeddingModel(**emb_data)
            self.session.add(embedding)
            models.append(embedding)
        await self.session.flush()
        return models

    async def get_by_chunk_id(self, chunk_id: int) -> EmbeddingModel | None:
        """Get embedding by chunk ID."""
        result = await self.session.execute(
            select(EmbeddingModel).where(EmbeddingModel.chunk_id == chunk_id)
        )
        return result.scalar_one_or_none()

    async def search_similar(
        self,
        query_vector: list[float],
        corpus_id: int,
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> list[ChunkWithScore]:
        """Search for similar chunks using pgvector cosine distance.

        Args:
            query_vector: Query embedding vector
            corpus_id: Corpus to search within
            top_k: Maximum number of results
            threshold: Minimum similarity score (0-1, higher is better)

        Returns:
            List of ChunkWithScore objects ordered by similarity
        """
        # Import pgvector distance function
        from sqlalchemy import text

        # Build query with cosine distance
        # cosine distance = 1 - cosine similarity
        # We want lower distance = higher similarity
        query_vec_str = "[" + ",".join(str(v) for v in query_vector) + "]"

        # Raw SQL for vector search with proper casting
        # Note: We embed the vector literal directly since asyncpg has issues with ::vector cast in params
        query = text(f"""
            SELECT
                c.id, c.file_id, c.chunk_type, c.name, c.start_line, c.end_line,
                c.text, c.token_count, c.hash,
                f.path as file_path,
                1 - (e.vector <=> '{query_vec_str}'::vector) as score
            FROM embedding e
            JOIN chunk c ON e.chunk_id = c.id
            JOIN file f ON c.file_id = f.id
            WHERE f.corpus_id = :corpus_id
            ORDER BY e.vector <=> '{query_vec_str}'::vector
            LIMIT :limit
        """)

        result = await self.session.execute(
            query,
            {
                "corpus_id": corpus_id,
                "limit": top_k,
            },
        )

        chunks_with_scores = []
        for row in result:
            chunk_id, file_id, chunk_type, name, start_line, end_line, text, token_count, hash, file_path, score = row

            # Filter by threshold if specified
            if score < threshold:
                continue

            chunks_with_scores.append(
                ChunkWithScore(
                    id=chunk_id,
                    file_id=file_id,
                    chunk_type=ChunkType(chunk_type),
                    name=name,
                    span=Span(
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                    ),
                    text=text,
                    token_count=token_count,
                    hash=hash,
                    score=float(score),
                )
            )

        return chunks_with_scores

    async def count_by_corpus(self, corpus_id: int) -> int:
        """Count embeddings in a corpus."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(EmbeddingModel.id))
            .join(ChunkModel)
            .join(FileModel)
            .where(FileModel.corpus_id == corpus_id)
        )
        return result.scalar() or 0


class QueryLogRepository:
    """Repository for query logging."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        query: str,
        latency_ms: float,
        corpus_id: int | None = None,
        answer: str | None = None,
        chunks_retrieved: int = 0,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        cost_estimate: float | None = None,
    ) -> QueryLogModel:
        """Create a query log entry."""
        log = QueryLogModel(
            corpus_id=corpus_id,
            query=query,
            answer=answer,
            latency_ms=latency_ms,
            chunks_retrieved=chunks_retrieved,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_estimate=cost_estimate,
        )
        self.session.add(log)
        await self.session.flush()
        return log


class SymbolRepository:
    """Repository for symbol operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        corpus_id: int,
        name: str,
        kind: SymbolKind,
        file_id: int,
        start_line: int,
        end_line: int,
        signature: str | None = None,
    ) -> SymbolModel:
        """Create a new symbol record."""
        symbol = SymbolModel(
            corpus_id=corpus_id,
            name=name,
            kind=kind,
            file_id=file_id,
            start_line=start_line,
            end_line=end_line,
            signature=signature,
        )
        self.session.add(symbol)
        await self.session.flush()
        return symbol

    async def batch_create(self, symbols: list[dict[str, Any]]) -> list[SymbolModel]:
        """Create multiple symbols at once."""
        models = []
        for symbol_data in symbols:
            symbol = SymbolModel(**symbol_data)
            self.session.add(symbol)
            models.append(symbol)
        await self.session.flush()
        return models

    async def get_by_id(self, symbol_id: int) -> SymbolModel | None:
        """Get symbol by ID."""
        result = await self.session.execute(
            select(SymbolModel).where(SymbolModel.id == symbol_id)
        )
        return result.scalar_one_or_none()

    async def find_by_name(
        self, corpus_id: int, name: str, kind: SymbolKind | None = None
    ) -> SymbolModel | None:
        """Find a symbol by name in a corpus."""
        query = select(SymbolModel).where(
            SymbolModel.corpus_id == corpus_id,
            SymbolModel.name.ilike(name),  # Case-insensitive
        )
        if kind:
            query = query.where(SymbolModel.kind == kind)
        result = await self.session.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def find_all_by_name(
        self, corpus_id: int, name: str
    ) -> list[SymbolModel]:
        """Find all symbols matching a name (for overloads)."""
        result = await self.session.execute(
            select(SymbolModel)
            .where(SymbolModel.corpus_id == corpus_id, SymbolModel.name.ilike(name))
            .order_by(SymbolModel.start_line)
        )
        return list(result.scalars().all())

    async def find_at_line(self, file_id: int, line: int) -> SymbolModel | None:
        """Find the symbol that contains a given line."""
        result = await self.session.execute(
            select(SymbolModel)
            .where(
                SymbolModel.file_id == file_id,
                SymbolModel.start_line <= line,
                SymbolModel.end_line >= line,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_corpus(
        self, corpus_id: int, kind: SymbolKind | None = None, limit: int = 100
    ) -> list[SymbolModel]:
        """List symbols in a corpus."""
        query = select(SymbolModel).where(SymbolModel.corpus_id == corpus_id)
        if kind:
            query = query.where(SymbolModel.kind == kind)
        query = query.order_by(SymbolModel.name).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_file(self, file_id: int) -> list[SymbolModel]:
        """List all symbols in a file."""
        result = await self.session.execute(
            select(SymbolModel)
            .where(SymbolModel.file_id == file_id)
            .order_by(SymbolModel.start_line)
        )
        return list(result.scalars().all())

    async def count_by_corpus(self, corpus_id: int) -> int:
        """Count symbols in a corpus."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(SymbolModel.id)).where(SymbolModel.corpus_id == corpus_id)
        )
        return result.scalar() or 0

    async def find_at_line(self, file_id: int, line: int) -> SymbolModel | None:
        """Find the symbol that contains a given line.

        Args:
            file_id: File ID to search in
            line: Line number to find containing symbol

        Returns:
            Symbol that contains the line, or None if not found
        """
        result = await self.session.execute(
            select(SymbolModel)
            .where(
                SymbolModel.file_id == file_id,
                SymbolModel.start_line <= line,
                SymbolModel.end_line >= line,
            )
            .order_by(SymbolModel.end_line - SymbolModel.start_line)  # Prefer smallest containing symbol
            .limit(1)
        )
        return result.scalar_one_or_none()


class ReferenceRepository:
    """Repository for reference operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        from_symbol_id: int | None,
        to_name: str,
        kind: ReferenceKind,
        file_id: int,
        line: int,
        to_symbol_id: int | None = None,
        snippet: str | None = None,
    ) -> ReferenceModel:
        """Create a new reference record."""
        reference = ReferenceModel(
            from_symbol_id=from_symbol_id,
            to_symbol_id=to_symbol_id,
            to_name=to_name,
            kind=kind,
            file_id=file_id,
            line=line,
            snippet=snippet,
        )
        self.session.add(reference)
        await self.session.flush()
        return reference

    async def batch_create(self, references: list[dict[str, Any]]) -> list[ReferenceModel]:
        """Create multiple references at once."""
        models = []
        for ref_data in references:
            reference = ReferenceModel(**ref_data)
            self.session.add(reference)
            models.append(reference)
        await self.session.flush()
        return models

    async def find_callers(
        self, corpus_id: int, symbol_name: str, limit: int = 100
    ) -> list[ReferenceModel]:
        """Find all references that call a symbol."""
        result = await self.session.execute(
            select(ReferenceModel)
            .join(SymbolModel, SymbolModel.id == ReferenceModel.from_symbol_id, isouter=True)
            .where(
                SymbolModel.corpus_id == corpus_id,
                ReferenceModel.to_name.ilike(symbol_name),
                ReferenceModel.kind == ReferenceKind.CALL,
            )
            .order_by(ReferenceModel.line)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_outgoing(
        self, symbol_id: int, kind: ReferenceKind | None = None
    ) -> list[ReferenceModel]:
        """Find all outgoing references from a symbol."""
        query = select(ReferenceModel).where(ReferenceModel.from_symbol_id == symbol_id)
        if kind:
            query = query.where(ReferenceModel.kind == kind)
        result = await self.session.execute(query.order_by(ReferenceModel.line))
        return list(result.scalars().all())

    async def find_dependencies(
        self, corpus_id: int, symbol_name: str
    ) -> list[ReferenceModel]:
        """Find INCLUDE/USE dependencies for a symbol."""
        # First find the symbol
        symbol_result = await self.session.execute(
            select(SymbolModel.id).where(
                SymbolModel.corpus_id == corpus_id,
                SymbolModel.name.ilike(symbol_name),
            )
        )
        symbol_id = symbol_result.scalar_one_or_none()
        if not symbol_id:
            return []

        # Find INCLUDE and USE references
        result = await self.session.execute(
            select(ReferenceModel)
            .where(
                ReferenceModel.from_symbol_id == symbol_id,
                ReferenceModel.kind.in_([ReferenceKind.INCLUDE, ReferenceKind.USE]),
            )
            .order_by(ReferenceModel.line)
        )
        return list(result.scalars().all())

    async def count_by_corpus(self, corpus_id: int) -> int:
        """Count references in a corpus."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(ReferenceModel.id))
            .join(SymbolModel, SymbolModel.id == ReferenceModel.from_symbol_id)
            .where(SymbolModel.corpus_id == corpus_id)
        )
        return result.scalar() or 0
