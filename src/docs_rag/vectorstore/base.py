"""Vector store contract: ids + vectors in, nearest ids by cosine similarity out."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class VectorStore(Protocol):
    kind: str

    def add(self, ids: list[str], vectors: np.ndarray) -> None: ...

    def search(self, query: np.ndarray, k: int) -> list[tuple[str, float]]:
        """Return up to k (id, cosine_score) pairs, best first."""
        ...

    def __len__(self) -> int: ...

    def clear(self) -> None: ...

    def save(self, path: Path) -> None: ...

    def load(self, path: Path) -> None: ...
