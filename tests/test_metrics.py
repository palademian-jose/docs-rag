from __future__ import annotations

import math

import pytest

from docs_rag.evals.metrics import (
    hit_at_k,
    mean,
    mrr,
    ndcg_at_k,
    percentile,
    precision_at_k,
    recall_at_k,
)

FLAGS = [False, True, False, False, True]  # relevant at ranks 2 and 5


def test_recall_and_precision() -> None:
    assert recall_at_k(FLAGS, 1, 2) == 0.0
    assert recall_at_k(FLAGS, 2, 2) == 0.5
    assert recall_at_k(FLAGS, 5, 2) == 1.0
    assert recall_at_k(FLAGS, 5, 0) == 0.0
    assert precision_at_k(FLAGS, 5) == pytest.approx(0.4)
    assert precision_at_k(FLAGS, 2) == pytest.approx(0.5)
    assert precision_at_k([], 5) == 0.0
    assert hit_at_k(FLAGS, 1) == 0.0 and hit_at_k(FLAGS, 2) == 1.0


def test_mrr() -> None:
    assert mrr(FLAGS) == 0.5
    assert mrr([True]) == 1.0
    assert mrr([False, False]) == 0.0


def test_ndcg_known_value() -> None:
    # hits at ranks 2 and 5: DCG = 1/log2(3) + 1/log2(6); IDCG for 2 relevant = 1 + 1/log2(3)
    dcg = 1 / math.log2(3) + 1 / math.log2(6)
    idcg = 1 + 1 / math.log2(3)
    assert ndcg_at_k(FLAGS, 10, 2) == pytest.approx(dcg / idcg)
    assert ndcg_at_k([True, True], 10, 2) == 1.0
    assert ndcg_at_k([False], 10, 1) == 0.0
    assert ndcg_at_k([True], 10, 0) == 0.0


def test_mean_and_percentile() -> None:
    assert mean([]) == 0.0
    assert mean([1, 2, 3]) == 2.0
    assert percentile([], 95) == 0.0
    values = list(range(1, 101))
    assert percentile(values, 50) == 50
    assert percentile(values, 95) == 95
    assert percentile(values, 100) == 100
    assert percentile([5.0], 95) == 5.0
