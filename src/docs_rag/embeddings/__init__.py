"""Embedding backends: fake (hashed bag-of-words), openai, local (sentence-transformers)."""

from __future__ import annotations

from docs_rag.embeddings.base import Embedder, l2_normalise
from docs_rag.embeddings.fake import FakeEmbedder
from docs_rag.settings import Settings, get_settings


def get_embedder(settings: Settings | None = None) -> Embedder:
    settings = settings or get_settings()
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("EMBEDDING_PROVIDER=openai needs OPENAI_API_KEY")
        from docs_rag.embeddings.openai_embed import OpenAIEmbedder

        return OpenAIEmbedder(settings.openai_api_key, model=settings.embedding_model)
    if settings.embedding_provider == "local":
        from docs_rag.embeddings.local import LocalEmbedder

        return LocalEmbedder()
    return FakeEmbedder(dim=settings.embedding_dim)


__all__ = ["Embedder", "FakeEmbedder", "get_embedder", "l2_normalise"]
