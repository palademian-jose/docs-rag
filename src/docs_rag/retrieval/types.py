"""Shared retrieval result type."""

from __future__ import annotations

from dataclasses import dataclass

from docs_rag.ingest.chunking import Chunk


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float
    rank: int  # 1-based
    source: str  # "dense" | "bm25" | "rrf" | "rerank"

    @property
    def chunk_id(self) -> str:
        return self.chunk.chunk_id
