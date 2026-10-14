"""Reranker contract: score (query, chunk) pairs and keep the best."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docs_rag.retrieval.types import RetrievedChunk


@runtime_checkable
class Reranker(Protocol):
    name: str
    model_name: str

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        """Return the top_k candidates re-scored, best first, with ``source="rerank"``."""
        ...


def take_top(scored: list[tuple[RetrievedChunk, float]], top_k: int) -> list[RetrievedChunk]:
    ordered = sorted(scored, key=lambda item: (-item[1], item[0].chunk_id))[:top_k]
    return [
        RetrievedChunk(item.chunk, score, rank, "rerank")
        for rank, (item, score) in enumerate(ordered, start=1)
    ]
