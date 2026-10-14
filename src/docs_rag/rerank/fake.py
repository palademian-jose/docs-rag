"""Lexical-overlap reranker used when no cross-encoder or API is available.

Score = 0.7 * (fraction of query terms present in the chunk)
      + 0.3 * (best single-sentence overlap), so chunks that answer the question in one place
        beat chunks that merely mention every term somewhere.
"""

from __future__ import annotations

from docs_rag.rerank.base import take_top
from docs_rag.retrieval.types import RetrievedChunk
from docs_rag.textutil import content_tokens, overlap_ratio, split_sentences


class FakeReranker:
    name = "fake"
    model_name = "fake-lexical-overlap"

    def score(self, query: str, text: str) -> float:
        q = content_tokens(query)
        if not q:
            return 0.0
        chunk_overlap = overlap_ratio(q, content_tokens(text))
        best_sentence = max(
            (overlap_ratio(q, content_tokens(s)) for s in split_sentences(text)), default=0.0
        )
        return 0.7 * chunk_overlap + 0.3 * best_sentence

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        scored = [(c, self.score(query, c.chunk.embed_text)) for c in candidates]
        return take_top(scored, top_k)
