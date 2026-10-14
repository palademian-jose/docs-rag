"""Ranking metrics over a list of relevance flags in rank order."""

from __future__ import annotations

import math
from collections.abc import Sequence


def recall_at_k(flags: Sequence[bool], k: int, n_relevant: int) -> float:
    if n_relevant <= 0:
        return 0.0
    return min(1.0, sum(1 for f in flags[:k] if f) / n_relevant)


def hit_at_k(flags: Sequence[bool], k: int) -> float:
    return 1.0 if any(flags[:k]) else 0.0


def precision_at_k(flags: Sequence[bool], k: int) -> float:
    if k <= 0:
        return 0.0
    return sum(1 for f in flags[:k] if f) / k


def mrr(flags: Sequence[bool]) -> float:
    for rank, flag in enumerate(flags, start=1):
        if flag:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(flags: Sequence[bool], k: int, n_relevant: int) -> float:
    dcg = sum(1.0 / math.log2(rank + 1) for rank, f in enumerate(flags[:k], start=1) if f)
    ideal_hits = min(n_relevant, k)
    if ideal_hits <= 0:
        return 0.0
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank percentile (p in [0, 100])."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, math.ceil(p / 100 * len(ordered)) - 1))
    return ordered[idx]
