"""Query API endpoint for LegacyLens."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from legacylens.core.config import get_settings
from legacylens.core.schemas import QueryRequest, QueryResponse
from legacylens.db import CorpusRepository, QueryLogRepository, get_db_session
from legacylens.generation import AnswerGenerator
from legacylens.retrieval import Searcher

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    session: AsyncSession = Depends(get_db_session),
) -> QueryResponse:
    """Process a natural language query against the codebase.

    Args:
        request: Query request with query text and optional parameters
        session: Database session

    Returns:
        QueryResponse with answer, citations, and retrieved chunks

    Raises:
        HTTPException: If no ready corpus is found or query processing fails
    """
    start_time = time.time()

    settings = get_settings()

    # Get corpus
    corpus_repo = CorpusRepository(session)
    if request.corpus_id:
        corpus = await corpus_repo.get_by_id(request.corpus_id)
        if not corpus:
            raise HTTPException(status_code=404, detail=f"Corpus {request.corpus_id} not found")
    else:
        corpus = await corpus_repo.get_ready_corpus()
        if not corpus:
            raise HTTPException(
                status_code=503,
                detail="No ready corpus available. Please ingest a corpus first.",
            )

    # Search for relevant chunks
    searcher = Searcher()
    try:
        chunks = await searcher.search(
            session=session,
            query=request.query,
            corpus_id=corpus.id,
            top_k=request.top_k,
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    # Generate answer
    generator = AnswerGenerator()
    try:
        response = await generator.generate_answer(
            query=request.query,
            chunks=chunks,
            max_chunks=request.top_k,
        )
    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {str(e)}")

    # Log query
    latency_ms = (time.time() - start_time) * 1000
    query_log_repo = QueryLogRepository(session)
    await query_log_repo.create(
        query=request.query,
        latency_ms=latency_ms,
        corpus_id=corpus.id,
        answer=response.answer[:500] if response.answer else None,
        chunks_retrieved=len(chunks),
    )

    logger.info(f"Query processed in {latency_ms:.1f}ms: {request.query[:50]}...")

    return response
