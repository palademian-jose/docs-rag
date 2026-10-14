"""Judge calibration: agreement with human labels, position-swap and length-bias checks."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from docs_rag.evals.judge import Judge
from docs_rag.evals.metrics import mean


def cohen_kappa(a: Sequence[bool], b: Sequence[bool]) -> float:
    """Cohen's kappa for two binary raters. Returns 1.0 when both agree perfectly on a constant."""
    if len(a) != len(b):
        raise ValueError("label sequences must have the same length")
    n = len(a)
    if n == 0:
        return 0.0
    agree = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    pa = sum(1 for x in a if x) / n
    pb = sum(1 for y in b if y) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    if expected >= 1.0:
        return 1.0 if agree == 1.0 else 0.0
    return (agree - expected) / (1 - expected)


def agreement(a: Sequence[bool], b: Sequence[bool]) -> float:
    if not a:
        return 0.0
    return sum(1 for x, y in zip(a, b, strict=True) if x == y) / len(a)


def position_swap_consistency(judge: Judge, criterion: str, rows: list[dict[str, Any]]) -> float:
    """Fraction of rows whose verdict is unchanged when the context order is reversed.

    A position-sensitive judge is one that rewards whatever chunk appears first.
    """
    if not rows:
        return 0.0
    same = 0
    for row in rows:
        inp = {"question": row["question"]}
        out = {"answer": row["answer"], "context": list(row.get("context", []))}
        ref = {"answer": row["expected_answer"]} if row.get("expected_answer") else None
        first = judge.judge(criterion, inp, out, ref)["pass"]
        swapped = dict(out, context=list(reversed(out["context"])))
        second = judge.judge(criterion, inp, swapped, ref)["pass"]
        same += int(first == second)
    return same / len(rows)


def length_bias(verdicts: Sequence[bool], lengths: Sequence[int]) -> dict[str, float]:
    """Compare answer lengths between passed and failed verdicts.

    Reports the mean length of each group and a point-biserial correlation between length and
    verdict; a strongly positive value means the judge favours long answers.
    """
    passed = [ln for v, ln in zip(verdicts, lengths, strict=True) if v]
    failed = [ln for v, ln in zip(verdicts, lengths, strict=True) if not v]
    n = len(lengths)
    corr = 0.0
    if passed and failed and n > 1:
        overall_mean = mean(list(lengths))
        sd = (sum((ln - overall_mean) ** 2 for ln in lengths) / n) ** 0.5
        if sd > 0:
            p = len(passed) / n
            corr = (mean(passed) - mean(failed)) / sd * (p * (1 - p)) ** 0.5
    return {
        "mean_length_pass": round(mean(passed), 1) if passed else 0.0,
        "mean_length_fail": round(mean(failed), 1) if failed else 0.0,
        "point_biserial": round(corr, 3),
    }
