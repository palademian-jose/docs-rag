"""Deterministic hashed bag-of-words embedder.

Each content token is hashed to a bucket with a sign (feature hashing), weighted by log(1 + tf)
and the vector is L2-normalised, so cosine similarity behaves like a crude lexical similarity.
It is good enough for the fake pipeline to retrieve the right chunk most of the time, and it is
fully deterministic across runs and machines.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter

import numpy as np

from docs_rag.embeddings.base import l2_normalise
from docs_rag.textutil import content_tokens


def _bucket(token: str, dim: int) -> tuple[int, float]:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    sign = 1.0 if value & 1 else -1.0
    return (value >> 1) % dim, sign


class FakeEmbedder:
    provider = "fake"

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim
        self.model_name = f"fake-hashed-bow-{dim}"

    def embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        counts = Counter(content_tokens(text))
        for token, tf in counts.items():
            idx, sign = _bucket(token, self.dim)
            vec[idx] += sign * math.log1p(tf)
        return vec

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return l2_normalise(np.stack([self.embed_one(t) for t in texts]))
