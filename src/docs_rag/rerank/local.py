"""Local cross-encoder reranker (optional extra: ``uv sync --extra local``)."""

from __future__ import annotations

from docs_rag.rerank.base import take_top
from docs_rag.retrieval.types import RetrievedChunk


class LocalReranker:
    name = "local"

    def __init__(self, model: str = "BAAI/bge-reranker-v2-m3") -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "RERANKER=local needs sentence-transformers: uv sync --extra local"
            ) from exc
        self.model_name = model
        self._model = CrossEncoder(model)

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []
        pairs = [(query, c.chunk.embed_text) for c in candidates]
        scores = self._model.predict(pairs, batch_size=16, show_progress_bar=False)
        scored = [(c, float(s)) for c, s in zip(candidates, scores, strict=True)]
        return take_top(scored, top_k)
