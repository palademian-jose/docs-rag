"""Sparse lexical retriever (BM25 Okapi via rank_bm25)."""

from __future__ import annotations

import numpy as np
from rank_bm25 import BM25Okapi

from docs_rag.ingest.chunking import Chunk
from docs_rag.retrieval.types import RetrievedChunk
from docs_rag.textutil import content_tokens


class BM25Retriever:
    name = "bm25"

    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = list(chunks)
        corpus = [content_tokens(c.embed_text) or ["<empty>"] for c in self.chunks]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        if self._bm25 is None or k <= 0:
            return []
        tokens = content_tokens(query)
        if not tokens:
            return []
        scores = np.asarray(self._bm25.get_scores(tokens), dtype=np.float64)
        k = min(k, len(self.chunks))
        order = np.argsort(-scores, kind="stable")[:k]
        out: list[RetrievedChunk] = []
        for rank, idx in enumerate(order, start=1):
            if scores[idx] <= 0:
                break
            out.append(RetrievedChunk(self.chunks[int(idx)], float(scores[idx]), rank, self.name))
        return out
