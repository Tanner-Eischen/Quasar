"""Retrieval search module for LegacyLens.

Provides vector similarity search for finding relevant code chunks.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from legacylens.core.schemas import ChunkWithScore
from legacylens.db.repository import CorpusRepository, EmbeddingRepository
from legacylens.embedding.embedder import EmbeddingClient

logger = logging.getLogger(__name__)


class Searcher:
    """RAG search orchestrator that combines embedding generation with vector search."""

    def __init__(
        self,
        embedding_client: EmbeddingClient | None = None,
    ):
        """Initialize the searcher.

        Args:
            embedding_client: Client for generating embeddings (created if not provided)
        """
        self.embedding_client = embedding_client or EmbeddingClient()

    async def search(
        self,
        session: AsyncSession,
        query: str,
        corpus_id: int | None = None,
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> list[ChunkWithScore]:
        """Search for relevant code chunks using semantic similarity.

        Args:
            session: Database session
            query: Natural language query text
            corpus_id: Corpus to search (if None, uses most recent READY corpus)
            top_k: Maximum number of results to return
            threshold: Minimum similarity score (0-1)

        Returns:
            List of ChunkWithScore objects ordered by relevance
        """
        # Get corpus to search
        corpus_repo = CorpusRepository(session)

        if corpus_id is None:
            corpus = await corpus_repo.get_ready_corpus()
            if corpus is None:
                logger.warning("No ready corpus found for search")
                return []
            corpus_id = corpus.id
        else:
            corpus = await corpus_repo.get_by_id(corpus_id)
            if corpus is None:
                logger.warning(f"Corpus {corpus_id} not found")
                return []

        logger.info(f"Searching corpus {corpus_id} for: {query[:100]}...")

        # Generate query embedding
        try:
            query_embedding = await self.embedding_client.embed(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []

        # Search for similar chunks
        embedding_repo = EmbeddingRepository(session)
        results = await embedding_repo.search_similar(
            query_vector=query_embedding,
            corpus_id=corpus_id,
            top_k=top_k,
            threshold=threshold,
        )

        logger.info(f"Found {len(results)} relevant chunks")
        return results

    async def search_with_fallback(
        self,
        session: AsyncSession,
        query: str,
        corpus_id: int | None = None,
        top_k: int = 10,
        min_results: int = 3,
    ) -> list[ChunkWithScore]:
        """Search with relaxed threshold if initial results are sparse.

        Args:
            session: Database session
            query: Natural language query text
            corpus_id: Corpus to search (if None, uses most recent READY corpus)
            top_k: Maximum number of results to return
            min_results: Minimum results desired (will lower threshold if needed)

        Returns:
            List of ChunkWithScore objects
        """
        # Try with default threshold
        results = await self.search(
            session=session,
            query=query,
            corpus_id=corpus_id,
            top_k=top_k,
            threshold=0.0,
        )

        # If we got enough results, return them
        if len(results) >= min_results:
            return results

        # Otherwise, results are already unfiltered (threshold=0.0)
        return results
