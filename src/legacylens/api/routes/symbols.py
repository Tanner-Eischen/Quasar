"""Symbol API endpoints for code understanding."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from legacylens.core.schemas import (
    CallSite,
    CallSitesResponse,
    ImpactReport,
    Symbol,
    SymbolResponse,
    UsageReference,
    UsageResponse,
)
from legacylens.db import (
    ChunkRepository,
    FileRepository,
    get_db_session,
)
from legacylens.db.models import FileModel, ReferenceModel, SymbolModel
from legacylens.db.repository import ReferenceRepository, SymbolRepository
from legacylens.generation import AnswerGenerator

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_corpus_id(session: AsyncSession, corpus_id: int | None) -> int:
    """Get corpus ID, defaulting to the most recent READY corpus."""
    if corpus_id:
        return corpus_id

    from legacylens.db import CorpusRepository

    corpus_repo = CorpusRepository(session)
    # This is a sync call in an async context, but we need the result
    # In a real implementation, we'd make this async
    import asyncio

    corpus = asyncio.get_event_loop().run_until_complete(corpus_repo.get_ready_corpus())
    if not corpus:
        raise HTTPException(
            status_code=503,
            detail="No ready corpus available. Please ingest a corpus first.",
        )
    return corpus.id


async def _get_ready_corpus_id(session: AsyncSession, corpus_id: int | None) -> int:
    """Get corpus ID, defaulting to the most recent READY corpus."""
    if corpus_id:
        return corpus_id

    from legacylens.db import CorpusRepository

    corpus_repo = CorpusRepository(session)
    corpus = await corpus_repo.get_ready_corpus()
    if not corpus:
        raise HTTPException(
            status_code=503,
            detail="No ready corpus available. Please ingest a corpus first.",
        )
    return corpus.id


@router.get("/symbols/{name}")
async def get_symbol(
    name: str,
    corpus_id: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> SymbolResponse:
    """Explain what a symbol does.

    Args:
        name: Symbol name to look up
        corpus_id: Corpus to search (optional, uses latest READY corpus)
        session: Database session

    Returns:
        SymbolResponse with symbol details and explanation
    """
    corpus_id = await _get_ready_corpus_id(session, corpus_id)

    # Find symbol
    symbol_repo = SymbolRepository(session)
    symbol = await symbol_repo.find_by_name(corpus_id, name)

    if not symbol:
        raise HTTPException(status_code=404, detail=f"Symbol '{name}' not found")

    # Get the file for path info
    file_repo = FileRepository(session)
    file = await file_repo.get_by_id(symbol.file_id)
    if not file:
        raise HTTPException(status_code=500, detail="Symbol's file not found")

    # Get chunk containing symbol for source code
    chunk_repo = ChunkRepository(session)
    # Find chunk that contains this symbol
    chunks = await chunk_repo.list_by_file(symbol.file_id)
    source_chunk = None
    for chunk in chunks:
        if chunk.start_line <= symbol.start_line and chunk.end_line >= symbol.end_line:
            source_chunk = chunk
            break

    # Generate explanation
    generator = AnswerGenerator()
    source_text = source_chunk.text if source_chunk else f"SUBROUTINE {name}(...)"
    prompt = f"Explain what this Fortran {symbol.kind.value} does in 2-3 sentences:\n\n{source_text[:2000]}"

    try:
        explanation = await generator.llm_client.generate(
            system_prompt="You are a Fortran code expert. Explain code concisely in plain English.",
            user_prompt=prompt,
            temperature=0.3,
        )
    except Exception as e:
        logger.warning(f"Failed to generate explanation: {e}")
        explanation = f"This is a {symbol.kind.value} defined in {file.path}."

    return SymbolResponse(
        symbol=Symbol(
            id=symbol.id,
            corpus_id=symbol.corpus_id,
            name=symbol.name,
            kind=symbol.kind,
            file_id=symbol.file_id,
            span={
                "file_path": file.path,
                "start_line": symbol.start_line,
                "end_line": symbol.end_line,
            },
            signature=symbol.signature,
        ),
        explanation=explanation,
    )


@router.get("/symbols/{name}/call-sites")
async def get_call_sites(
    name: str,
    corpus_id: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> CallSitesResponse:
    """Find all places where a symbol is called.

    Args:
        name: Symbol name to find callers for
        corpus_id: Corpus to search (optional)
        session: Database session

    Returns:
        CallSitesResponse with list of call sites
    """
    corpus_id = await _get_ready_corpus_id(session, corpus_id)

    # Find all call references to this symbol
    ref_repo = ReferenceRepository(session)
    refs = await ref_repo.find_callers(corpus_id, name)

    call_sites = []
    for ref in refs:
        # Get the caller symbol
        result = await session.execute(
            select(SymbolModel)
            .options(selectinload(SymbolModel.outgoing_refs))
            .where(SymbolModel.id == ref.from_symbol_id)
        )
        caller = result.scalar_one_or_none()

        # Get the file
        file_result = await session.execute(
            select(FileModel).where(FileModel.id == ref.file_id)
        )
        file = file_result.scalar_one_or_none()

        if caller and file:
            call_sites.append(
                CallSite(
                    caller_name=caller.name,
                    caller_span={
                        "file_path": file.path,
                        "start_line": caller.start_line,
                        "end_line": caller.end_line,
                    },
                    callee_name=name,
                    snippet=ref.snippet or f"CALL {name}(...)",
                )
            )

    return CallSitesResponse(
        symbol_name=name,
        call_sites=call_sites,
    )


@router.get("/symbols/{name}/dependencies")
async def get_dependencies(
    name: str,
    corpus_id: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> UsageResponse:
    """Get INCLUDE/USE dependencies for a symbol.

    Args:
        name: Symbol name to find dependencies for
        corpus_id: Corpus to search (optional)
        session: Database session

    Returns:
        UsageResponse with list of dependencies
    """
    corpus_id = await _get_ready_corpus_id(session, corpus_id)

    # Find dependencies
    ref_repo = ReferenceRepository(session)
    refs = await ref_repo.find_dependencies(corpus_id, name)

    references = []
    for ref in refs:
        # Get file path
        file_result = await session.execute(
            select(FileModel).where(FileModel.id == ref.file_id)
        )
        file = file_result.scalar_one_or_none()

        if file:
            references.append(
                UsageReference(
                    from_file=file.path,
                    from_line=ref.line,
                    kind=ref.kind,
                    to_name=ref.to_name,
                    snippet=ref.snippet or f"{ref.kind.value} {ref.to_name}",
                )
            )

    return UsageResponse(
        symbol_name=name,
        references=references,
    )


@router.get("/symbols/{name}/impact")
async def get_impact_analysis(
    name: str,
    corpus_id: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ImpactReport:
    """Estimate blast radius of changing a symbol.

    Args:
        name: Symbol name to analyze
        corpus_id: Corpus to search (optional)
        session: Database session

    Returns:
        ImpactReport with callers and blast radius estimate
    """
    corpus_id = await _get_ready_corpus_id(session, corpus_id)

    ref_repo = ReferenceRepository(session)

    # Find direct callers
    direct_refs = await ref_repo.find_callers(corpus_id, name)
    direct_caller_ids = list(set(ref.from_symbol_id for ref in direct_refs))

    # Get names of direct callers
    direct_names = []
    files_affected = set()

    for ref in direct_refs:
        # Get caller symbol name
        result = await session.execute(
            select(SymbolModel).where(SymbolModel.id == ref.from_symbol_id)
        )
        caller = result.scalar_one_or_none()
        if caller:
            direct_names.append(caller.name)

        # Get file
        file_result = await session.execute(
            select(FileModel).where(FileModel.id == ref.file_id)
        )
        file = file_result.scalar_one_or_none()
        if file:
            files_affected.add(file.path)

    # Find indirect callers (callers of callers)
    indirect_names = set()
    for caller_name in direct_names:
        indirect_refs = await ref_repo.find_callers(corpus_id, caller_name)
        for ref in indirect_refs:
            result = await session.execute(
                select(SymbolModel).where(SymbolModel.id == ref.from_symbol_id)
            )
            indirect_caller = result.scalar_one_or_none()
            if indirect_caller and indirect_caller.name not in direct_names:
                indirect_names.add(indirect_caller.name)

            # Get file
            file_result = await session.execute(
                select(FileModel).where(FileModel.id == ref.file_id)
            )
            file = file_result.scalar_one_or_none()
            if file:
                files_affected.add(file.path)

    # Estimate blast radius
    total_callers = len(direct_names) + len(indirect_names)
    if total_callers < 5:
        blast_radius = "low"
    elif total_callers < 20:
        blast_radius = "medium"
    else:
        blast_radius = "high"

    return ImpactReport(
        symbol_name=name,
        direct_callers=direct_names,
        indirect_callers=list(indirect_names),
        files_affected=list(files_affected),
        estimated_blast_radius=blast_radius,
    )
