"""Graph API endpoint for visualization."""

import logging
import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from legacylens.core.schemas import ReferenceKind
from legacylens.db import FileRepository, get_db_session
from legacylens.db.models import FileModel, ReferenceModel, SymbolModel
from legacylens.db.repository import CorpusRepository, ReferenceRepository, SymbolRepository

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_ready_corpus_id(session: AsyncSession, corpus_id: int | None) -> int:
    """Get corpus ID, defaulting to the most recent READY corpus."""
    if corpus_id:
        return corpus_id

    corpus_repo = CorpusRepository(session)
    corpus = await corpus_repo.get_ready_corpus()
    if not corpus:
        raise HTTPException(
            status_code=503,
            detail="No ready corpus available. Please ingest a corpus first.",
        )
    return corpus.id


def _circular_layout(count: int, radius: float = 400, center_x: float = 600, center_y: float = 400) -> list[dict]:
    """Generate positions for nodes in a circular layout."""
    positions = []
    for i in range(count):
        angle = (2 * math.pi * i) / count - math.pi / 2  # Start from top
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        positions.append({"x": x, "y": y})
    return positions


@router.get("/graph/{corpus_id}")
async def get_graph(
    corpus_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get graph data for visualization.

    Returns nodes (files with symbols) and edges (call references).

    Args:
        corpus_id: Corpus ID to get graph for
        session: Database session

    Returns:
        Dict with nodes, edges, and stats
    """
    # Verify corpus exists
    corpus_repo = CorpusRepository(session)
    corpus = await corpus_repo.get_by_id(corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail=f"Corpus {corpus_id} not found")

    # Get all files
    file_repo = FileRepository(session)
    files = await file_repo.list_by_corpus(corpus_id)

    # Get all symbols with file info
    symbol_repo = SymbolRepository(session)
    symbols = await symbol_repo.list_by_corpus(corpus_id, limit=10000)

    # Get all CALL references
    ref_repo = ReferenceRepository(session)

    # Query all CALL references for this corpus
    result = await session.execute(
        select(ReferenceModel)
        .join(SymbolModel, SymbolModel.id == ReferenceModel.from_symbol_id)
        .where(
            SymbolModel.corpus_id == corpus_id,
            ReferenceModel.kind == ReferenceKind.CALL,
        )
    )
    call_refs = list(result.scalars().all())

    # Build symbol lookup by ID
    symbol_by_id = {s.id: s for s in symbols}

    # Build symbol count per file
    symbol_count_by_file: dict[int, int] = {}
    for sym in symbols:
        symbol_count_by_file[sym.file_id] = symbol_count_by_file.get(sym.file_id, 0) + 1

    # Generate circular layout for files
    file_positions = _circular_layout(len(files), radius=350, center_x=600, center_y=450)

    # Build nodes - file nodes (collapsed by default)
    nodes = []
    file_id_to_node_id: dict[int, str] = {}

    for i, file in enumerate(files):
        pos = file_positions[i]
        node_id = f"file-{file.id}"
        file_id_to_node_id[file.id] = node_id

        nodes.append({
            "id": node_id,
            "type": "file",
            "name": file.path.split("/")[-1],  # Just filename
            "path": file.path,
            "x": pos["x"],
            "y": pos["y"],
            "symbolCount": symbol_count_by_file.get(file.id, 0),
            "lineCount": file.line_count,
            "expanded": False,
        })

    # Build symbol node data (initially not visible, will be shown on expand)
    symbol_id_to_node_id: dict[int, str] = {}
    symbol_nodes_data = []

    for sym in symbols:
        node_id = f"symbol-{sym.id}"
        symbol_id_to_node_id[sym.id] = node_id
        file_node_id = file_id_to_node_id.get(sym.file_id)

        symbol_nodes_data.append({
            "id": node_id,
            "type": "symbol",
            "name": sym.name,
            "kind": sym.kind.value,
            "fileId": sym.file_id,
            "fileNodeId": file_node_id,
            "startLine": sym.start_line,
            "endLine": sym.end_line,
            "signature": sym.signature,
            # Position will be calculated when file is expanded
            "x": 0,
            "y": 0,
        })

    # Build edges - only CALL references with resolved symbols
    edges = []

    for ref in call_refs:
        from_id = symbol_id_to_node_id.get(ref.from_symbol_id)
        to_symbol = symbol_by_id.get(ref.to_symbol_id)

        # Only include edge if both symbols exist
        if from_id and to_symbol:
            to_id = symbol_id_to_node_id.get(to_symbol.id)
            if to_id:
                edges.append({
                    "id": f"edge-{ref.id}",
                    "type": "call",
                    "from": from_id,
                    "to": to_id,
                    "fromFileId": symbol_by_id[ref.from_symbol_id].file_id if ref.from_symbol_id else None,
                    "toFileId": to_symbol.file_id,
                    "line": ref.line,
                    "snippet": ref.snippet,
                })

    # Calculate stats
    stats = {
        "fileCount": len(files),
        "symbolCount": len(symbols),
        "callCount": len(edges),
        "corpusId": corpus_id,
        "repoUrl": corpus.repo_url,
    }

    return {
        "nodes": nodes,
        "symbolNodes": symbol_nodes_data,  # Separate array for lazy loading
        "edges": edges,
        "stats": stats,
    }


@router.get("/graph")
async def get_default_graph(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get graph data for the default (latest READY) corpus."""
    corpus_id = await _get_ready_corpus_id(session, None)
    return await get_graph(corpus_id, session)
