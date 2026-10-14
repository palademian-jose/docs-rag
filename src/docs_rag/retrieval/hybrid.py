"""Hybrid retriever: dense + BM25 candidates fused with Reciprocal Rank Fusion."""

from __future__ import annotations

from docs_rag.retrieval.bm25 import BM25Retriever
from docs_rag.retrieval.dense import DenseRetriever
from docs_rag.retrieval.fusion import rrf
from docs_rag.retrieval.types import RetrievedChunk


class HybridRetriever:
    name = "hybrid"

    def __init__(
        self,
        dense: DenseRetriever,
        bm25: BM25Retriever,
        *,
        candidates_per_retriever: int = 50,
        rrf_k: int = 60,
    ) -> None:
        self.dense = dense
        self.bm25 = bm25
        self.candidates_per_retriever = candidates_per_retriever
        self.rrf_k = rrf_k
        self.last_dense: list[RetrievedChunk] = []
        self.last_bm25: list[RetrievedChunk] = []

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        n = max(self.candidates_per_retriever, k)
        self.last_dense = self.dense.retrieve(query, n)
        self.last_bm25 = self.bm25.retrieve(query, n)
        by_id = {r.chunk_id: r.chunk for r in [*self.last_dense, *self.last_bm25]}
        fused = rrf(
            [[r.chunk_id for r in self.last_dense], [r.chunk_id for r in self.last_bm25]],
            k=self.rrf_k,
        )
        return [
            RetrievedChunk(by_id[cid], score, rank, "rrf")
            for rank, (cid, score) in enumerate(fused[:k], start=1)
        ]
