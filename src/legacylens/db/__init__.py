"""Database layer for LegacyLens."""

from legacylens.db.models import (
    Base,
    ChunkModel,
    CorpusModel,
    EmbeddingModel,
    FileModel,
    QueryLogModel,
    ReferenceModel,
    SymbolModel,
)
from legacylens.db.repository import (
    ChunkRepository,
    CorpusRepository,
    EmbeddingRepository,
    FileRepository,
    QueryLogRepository,
)
from legacylens.db.session import (
    close_db,
    get_db_session,
    get_engine,
    get_session_factory,
    init_db,
)

__all__ = [
    # Models
    "Base",
    "ChunkModel",
    "CorpusModel",
    "EmbeddingModel",
    "FileModel",
    "QueryLogModel",
    "ReferenceModel",
    "SymbolModel",
    # Repositories
    "ChunkRepository",
    "CorpusRepository",
    "EmbeddingRepository",
    "FileRepository",
    "QueryLogRepository",
    # Session management
    "close_db",
    "get_db_session",
    "get_engine",
    "get_session_factory",
    "init_db",
]
