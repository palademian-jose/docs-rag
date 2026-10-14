"""OpenAI embeddings backend (text-embedding-3-large by default)."""

from __future__ import annotations

import numpy as np

from docs_rag.embeddings.base import l2_normalise

_KNOWN_DIMS = {"text-embedding-3-large": 3072, "text-embedding-3-small": 1536}


class OpenAIEmbedder:
    provider = "openai"

    def __init__(
        self, api_key: str, *, model: str = "text-embedding-3-large", batch_size: int = 100
    ) -> None:
        from openai import OpenAI

        self.model_name = model
        self.dim = _KNOWN_DIMS.get(model, 1536)
        self.batch_size = batch_size
        self._client = OpenAI(api_key=api_key)
        self.last_usage_tokens = 0

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        rows: list[list[float]] = []
        self.last_usage_tokens = 0
        for i in range(0, len(texts), self.batch_size):
            batch = [t.replace("\n", " ") for t in texts[i : i + self.batch_size]]
            resp = self._client.embeddings.create(input=batch, model=self.model_name)
            rows.extend(d.embedding for d in resp.data)
            if resp.usage is not None:
                self.last_usage_tokens += resp.usage.total_tokens or 0
        vectors = np.asarray(rows, dtype=np.float32)
        self.dim = vectors.shape[1]
        return l2_normalise(vectors)
