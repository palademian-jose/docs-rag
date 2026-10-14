"""Vector store backends: memory (numpy + .npz) and pgvector."""

from __future__ import annotations

from docs_rag.settings import Settings, get_settings
from docs_rag.vectorstore.base import VectorStore
from docs_rag.vectorstore.memory import MemoryVectorStore


def get_vector_store(dim: int, settings: Settings | None = None) -> VectorStore:
    settings = settings or get_settings()
    if settings.vector_store == "pgvector":
        from docs_rag.vectorstore.pgvector_store import PgVectorStore

        return PgVectorStore(settings.pg_dsn, dim)
    return MemoryVectorStore(dim)


__all__ = ["MemoryVectorStore", "VectorStore", "get_vector_store"]
