"""Reciprocal Rank Fusion.

score(d) = sum over rankings r of 1 / (k + rank_r(d)), with rank starting at 1 and k = 60 by
default (Cormack, Clarke and Buettcher, 2009). Only ranks matter, so retrievers with
incomparable score scales (cosine in [-1, 1] versus unbounded BM25) can be fused without
calibration.
"""

from __future__ import annotations

from collections.abc import Sequence


def rrf(rankings: Sequence[Sequence[str]], *, k: int = 60) -> list[tuple[str, float]]:
    """Fuse ranked id lists; returns (id, score) best first, ties broken by id for determinism."""
    if k <= 0:
        raise ValueError("k must be positive")
    scores: dict[str, float] = {}
    for ranking in rankings:
        seen: set[str] = set()
        for rank, doc_id in enumerate(ranking, start=1):
            if doc_id in seen:
                continue
            seen.add(doc_id)
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
