"""Files API endpoints for LegacyLens."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from legacylens.db import FileRepository, get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


class FileResponse(BaseModel):
    """Response for file lookup."""

    path: str
    language: str
    line_count: int
    content: str
    hash: str


class FileInfoResponse(BaseModel):
    """Response for file info (without content)."""

    id: int
    path: str
    language: str
    line_count: int
    hash: str


@router.get("/file/{file_path:path}", response_model=FileResponse)
async def get_file(
    file_path: str,
    corpus_id: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    """Get file content and metadata.

    Args:
        file_path: Path to the file within the corpus
        corpus_id: Optional corpus ID (defaults to latest ready corpus)
        session: Database session

    Returns:
        FileResponse with content and metadata

    Raises:
        HTTPException: If file or corpus not found
    """
    from legacylens.db import CorpusRepository

    # Get corpus
    corpus_repo = CorpusRepository(session)
    if corpus_id:
        corpus = await corpus_repo.get_by_id(corpus_id)
    else:
        corpus = await corpus_repo.get_ready_corpus()

    if not corpus:
        raise HTTPException(
            status_code=503,
            detail="No ready corpus available.",
        )

    # Find file
    file_repo = FileRepository(session)
    file = await file_repo.get_by_path(corpus.id, file_path)

    if not file:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # Read file content from disk
    # Try corpus directory first
    content = None
    for corpus_dir in [Path("corpus"), Path("../corpus")]:
        full_path = corpus_dir / file_path
        if full_path.exists():
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                break
            except Exception as e:
                logger.error(f"Failed to read file {full_path}: {e}")

    if content is None:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read file from disk: {file_path}",
        )

    return FileResponse(
        path=file.path,
        language=file.language,
        line_count=file.line_count,
        content=content,
        hash=file.hash,
    )


@router.get("/files", response_model=list[FileInfoResponse])
async def list_files(
    corpus_id: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[FileInfoResponse]:
    """List all files in the corpus.

    Args:
        corpus_id: Optional corpus ID (defaults to latest ready corpus)
        session: Database session

    Returns:
        List of FileInfoResponse objects

    Raises:
        HTTPException: If corpus not found
    """
    from legacylens.db import CorpusRepository

    # Get corpus
    corpus_repo = CorpusRepository(session)
    if corpus_id:
        corpus = await corpus_repo.get_by_id(corpus_id)
    else:
        corpus = await corpus_repo.get_ready_corpus()

    if not corpus:
        raise HTTPException(
            status_code=503,
            detail="No ready corpus available.",
        )

    # List files
    file_repo = FileRepository(session)
    files = await file_repo.list_by_corpus(corpus.id)

    return [
        FileInfoResponse(
            id=f.id,
            path=f.path,
            language=f.language,
            line_count=f.line_count,
            hash=f.hash,
        )
        for f in files
    ]
