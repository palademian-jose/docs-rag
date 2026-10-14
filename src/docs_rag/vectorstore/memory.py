"""In-memory numpy vector store with .npz persistence."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from docs_rag.embeddings.base import l2_normalise


class MemoryVectorStore:
    kind = "memory"

    def __init__(self, dim: int | None = None) -> None:
        self._ids: list[str] = []
        self._vectors: np.ndarray = np.zeros((0, dim or 0), dtype=np.float32)

    def add(self, ids: list[str], vectors: np.ndarray) -> None:
        if len(ids) != len(vectors):
            raise ValueError("ids and vectors must have the same length")
        vectors = l2_normalise(np.asarray(vectors, dtype=np.float32))
        if self._vectors.shape[0] == 0:
            self._vectors = vectors.copy()
        else:
            self._vectors = np.vstack([self._vectors, vectors])
        self._ids.extend(ids)

    def search(self, query: np.ndarray, k: int) -> list[tuple[str, float]]:
        if not self._ids or k <= 0:
            return []
        q = l2_normalise(np.asarray(query, dtype=np.float32).reshape(1, -1))[0]
        scores = self._vectors @ q
        k = min(k, len(self._ids))
        top = np.argpartition(-scores, k - 1)[:k]
        top = top[np.argsort(-scores[top], kind="stable")]
        return [(self._ids[i], float(scores[i])) for i in top]

    def __len__(self) -> int:
        return len(self._ids)

    def clear(self) -> None:
        self._ids = []
        self._vectors = np.zeros((0, self._vectors.shape[1]), dtype=np.float32)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, ids=np.asarray(self._ids, dtype=object), vectors=self._vectors)

    def load(self, path: Path) -> None:
        data = np.load(Path(path), allow_pickle=True)
        self._ids = [str(x) for x in data["ids"].tolist()]
        self._vectors = np.asarray(data["vectors"], dtype=np.float32)
