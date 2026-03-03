"""
Graph API Endpoint for LegacyLens
File: src/legacylens/api/routes/graph.py

Returns file nodes, symbol nodes, and call edges for visualization.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
import math

from src.legacylens.db.session import get_session
from src.legacylens.db.models import (
    File as FileModel,
    Symbol as SymbolModel,
    Reference as ReferenceModel,
)

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


@router.get("/{corpus_id}")
async def get_graph(
    corpus_id: int,
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Get the call graph for a corpus.
    
    Returns:
        {
            "nodes": [
                {
                    "id": "file-1",
                    "type": "file",
                    "path": "hazard/hazgridX.f",
                    "name": "hazgridX.f",
                    "symbolCount": 12,
                    "x": 200.0,
                    "y": 200.0
                },
                {
                    "id": "sym-45",
                    "type": "symbol",
                    "name": "getABsub",
                    "kind": "SUBROUTINE",
                    "fileId": "file-1",
                    "line": 45,
                    "x": 0,  // Will be positioned by frontend when expanded
                    "y": 0
                }
            ],
            "edges": [
                {
                    "id": "call-123",
                    "from": "sym-45",
                    "to": "sym-78",
                    "type": "symbol-to-symbol",
                    "kind": "CALL",
                    "line": 67,
                    "snippet": "CALL hazSUBX(params)"
                },
                {
                    "id": "call-456",
                    "from": "file-12",
                    "to": "sym-90",
                    "type": "file-to-symbol",
                    "kind": "CALL",
                    "line": 145,
                    "snippet": "CALL getABsub(...)"
                }
            ],
            "stats": {
                "fileCount": 27,
                "symbolCount": 1163,
                "callCount": 1054,
                "linkedCalls": 19,
                "unlinkdCalls": 1035
            }
        }
    """
    
    # Fetch all files
    files_stmt = select(FileModel).where(FileModel.corpus_id == corpus_id)
    files_result = await session.execute(files_stmt)
    files = files_result.scalars().all()
    
    if not files:
        raise HTTPException(status_code=404, detail=f"Corpus {corpus_id} not found or has no files")
    
    # Fetch all symbols
    symbols_stmt = select(SymbolModel).where(SymbolModel.corpus_id == corpus_id)
    symbols_result = await session.execute(symbols_stmt)
    symbols = symbols_result.scalars().all()
    
    # Fetch all references (both linked and unlinked)
    refs_stmt = select(ReferenceModel).where(
        ReferenceModel.file_id.in_([f.id for f in files])
    )
    refs_result = await session.execute(refs_stmt)
    references = refs_result.scalars().all()
    
    # Group symbols by file for counting
    symbols_by_file = {}
    for symbol in symbols:
        if symbol.file_id not in symbols_by_file:
            symbols_by_file[symbol.file_id] = []
        symbols_by_file[symbol.file_id].append(symbol)
    
    # Create symbol lookup by name for unlinked references
    symbols_by_name = {s.name.upper(): s for s in symbols}
    
    # ====================================================================
    # BUILD NODES
    # ====================================================================
    
    nodes = []
    
    # File nodes - arrange in circular layout
    radius = 400  # Initial radius for circular arrangement
    for i, file in enumerate(files):
        angle = 2 * math.pi * i / len(files)
        nodes.append({
            "id": f"file-{file.id}",
            "type": "file",
            "path": file.path,
            "name": file.path.split("/")[-1],  # Just filename
            "symbolCount": len(symbols_by_file.get(file.id, [])),
            "x": radius * math.cos(angle),
            "y": radius * math.sin(angle),
            # Future 2.5D: add "z": 0
        })
    
    # Symbol nodes - initially at (0, 0), positioned by frontend when file expands
    for symbol in symbols:
        nodes.append({
            "id": f"sym-{symbol.id}",
            "type": "symbol",
            "name": symbol.name,
            "kind": symbol.kind,
            "fileId": f"file-{symbol.file_id}",
            "line": symbol.start_line,
            "signature": symbol.signature,
            "x": 0,
            "y": 0,
            # Future 2.5D: add "z": 100 (floats above file layer)
        })
    
    # ====================================================================
    # BUILD EDGES
    # ====================================================================
    
    edges = []
    linked_count = 0
    unlinked_count = 0
    
    for ref in references:
        # Try to resolve the target symbol
        to_symbol_id = None
        
        if ref.to_symbol_id:
            # Already resolved in database
            to_symbol_id = ref.to_symbol_id
        elif ref.to_name:
            # Try to resolve by name
            symbol = symbols_by_name.get(ref.to_name.upper())
            if symbol:
                to_symbol_id = symbol.id
        
        if not to_symbol_id:
            # Can't resolve target, skip this edge
            continue
        
        # Determine edge type and source
        if ref.from_symbol_id:
            # Symbol-to-symbol call (1.8% of refs)
            edge_type = "symbol-to-symbol"
            from_id = f"sym-{ref.from_symbol_id}"
            linked_count += 1
        else:
            # File-to-symbol call (98.2% of refs - main program calls)
            edge_type = "file-to-symbol"
            from_id = f"file-{ref.file_id}"
            unlinked_count += 1
        
        edges.append({
            "id": f"call-{ref.id}",
            "from": from_id,
            "to": f"sym-{to_symbol_id}",
            "type": edge_type,
            "kind": ref.kind,
            "line": ref.line,
            "snippet": ref.snippet[:100] if ref.snippet else "",  # Truncate long snippets
            # Future 2.5D: edges will need 3D coordinates
        })
    
    # ====================================================================
    # RETURN RESPONSE
    # ====================================================================
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "fileCount": len(files),
            "symbolCount": len(symbols),
            "callCount": len(edges),
            "linkedCalls": linked_count,
            "unlinkedCalls": unlinked_count,
        }
    }


# ====================================================================
# INTEGRATION INSTRUCTIONS
# ====================================================================

"""
1. Create file: src/legacylens/api/routes/graph.py
2. Copy the code above into it

3. Update src/legacylens/api/main.py:
   
   from src.legacylens.api.routes import graph
   
   app.include_router(graph.router)

4. Test the endpoint:
   
   curl http://localhost:8000/api/v1/graph/1 | jq '.stats'
   
   Expected output:
   {
     "fileCount": 27,
     "symbolCount": 1163,
     "callCount": ~1000,
     "linkedCalls": 19,
     "unlinkedCalls": ~1035
   }

5. Frontend will consume this data to render the graph
"""
