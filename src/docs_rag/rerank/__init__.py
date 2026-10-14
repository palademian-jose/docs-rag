"""Rerankers: fake (lexical overlap), cohere (Rerank API), local (cross-encoder)."""

from __future__ import annotations

from docs_rag.rerank.base import Reranker
from docs_rag.rerank.fake import FakeReranker
from docs_rag.settings import Settings


def get_reranker(settings: Settings, *, kind: str | None = None) -> Reranker | None:
    kind = kind or settings.reranker
    if kind == "none":
        return None
    if kind == "cohere":
        if not settings.cohere_api_key:
            raise RuntimeError("RERANKER=cohere needs COHERE_API_KEY")
        from docs_rag.rerank.cohere import CohereReranker

        return CohereReranker(settings.cohere_api_key)
    if kind == "local":
        from docs_rag.rerank.local import LocalReranker

        return LocalReranker()
    return FakeReranker()


__all__ = ["FakeReranker", "Reranker", "get_reranker"]
