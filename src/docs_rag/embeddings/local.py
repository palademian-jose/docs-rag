"""Local sentence-transformers embedder (optional extra: ``uv sync --extra local``)."""

from __future__ import annotations

import numpy as np

from docs_rag.embeddings.base import l2_normalise


class LocalEmbedder:
    provider = "local"

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "EMBEDDING_PROVIDER=local needs sentence-transformers: uv sync --extra local"
            ) from exc
        self.model_name = model
        self._model = SentenceTransformer(model)
        self.dim = int(self._model.get_sentence_embedding_dimension() or 384)

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vectors = self._model.encode(texts, batch_size=32, show_progress_bar=False)
        return l2_normalise(np.asarray(vectors, dtype=np.float32))
