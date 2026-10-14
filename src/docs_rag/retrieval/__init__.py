"""Retrievers: dense, BM25 and hybrid (RRF)."""

from __future__ import annotations

from docs_rag.ingest.index import Index
from docs_rag.retrieval.bm25 import BM25Retriever
from docs_rag.retrieval.dense import DenseRetriever
from docs_rag.retrieval.fusion import rrf
from docs_rag.retrieval.hybrid import HybridRetriever
from docs_rag.retrieval.types import RetrievedChunk
from docs_rag.settings import Settings
from docs_rag.tracing import Tracer


def build_retriever(
    index: Index,
    settings: Settings,
    *,
    mode: str | None = None,
    tracer: Tracer | None = None,
) -> DenseRetriever | HybridRetriever:
    mode = mode or settings.retrieval_mode
    dense = DenseRetriever(index, tracer=tracer)
    if mode == "dense":
        return dense
    return HybridRetriever(
        dense,
        BM25Retriever(index.chunks),
        candidates_per_retriever=settings.candidates_per_retriever,
        rrf_k=settings.rrf_k,
    )


__all__ = [
    "BM25Retriever",
    "DenseRetriever",
    "HybridRetriever",
    "RetrievedChunk",
    "build_retriever",
    "rrf",
]
