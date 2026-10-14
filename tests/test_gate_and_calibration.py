from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from docs_rag.evals.calibration import (
    agreement,
    cohen_kappa,
    length_bias,
    position_swap_consistency,
)
from docs_rag.evals.gate import evaluate_gate, load_gate_config, render_markdown
from docs_rag.evals.judge import LexicalJudge

CONFIG = {
    "faithfulness": {"min": 0.85, "max_drop": 0.05},
    "recall_at_20": {"min": 0.80, "max_drop": 0.05},
    "hallucination": {"max": 0.10, "max_rise": 0.05},
}


def _result(**metrics: float) -> dict:
    return {"metrics": metrics}


def test_gate_passes_when_within_thresholds() -> None:
    base = _result(faithfulness=0.90, recall_at_20=0.85, hallucination=0.05)
    cand = _result(faithfulness=0.88, recall_at_20=0.86, hallucination=0.06)
    ok, rows = evaluate_gate(base, cand, CONFIG)
    assert ok and all(r.ok for r in rows)
    md = render_markdown(rows, ok=ok)
    assert "**Gate: PASS**" in md and "| faithfulness |" in md


def test_gate_fails_on_drop_min_and_rise() -> None:
    base = _result(faithfulness=0.95, recall_at_20=0.85, hallucination=0.02)
    cand = _result(faithfulness=0.88, recall_at_20=0.70, hallucination=0.09)
    ok, rows = evaluate_gate(base, cand, CONFIG)
    assert not ok
    by_metric = {r.metric: r for r in rows}
    assert not by_metric["faithfulness"].ok and "dropped" in by_metric["faithfulness"].note
    assert not by_metric["recall_at_20"].ok and "below min" in by_metric["recall_at_20"].note
    assert not by_metric["hallucination"].ok and "rose" in by_metric["hallucination"].note
    assert "**Gate: FAIL**" in render_markdown(rows, ok=ok)


def test_gate_without_baseline_and_missing_metric() -> None:
    cand = _result(faithfulness=0.90, recall_at_20=0.85)
    ok, rows = evaluate_gate(None, cand, CONFIG)
    assert not ok
    by_metric = {r.metric: r for r in rows}
    assert by_metric["faithfulness"].ok and "no baseline" in by_metric["faithfulness"].note
    assert not by_metric["hallucination"].ok and "missing" in by_metric["hallucination"].note


def test_gate_config_file_and_cli(tmp_path: Path) -> None:
    cfg = load_gate_config(Path("evals.yaml"))
    assert "faithfulness" in cfg and "recall_at_20" in cfg
    base = tmp_path / "base.json"
    cand = tmp_path / "cand.json"
    base.write_text(json.dumps(_result(faithfulness=0.9, recall_at_20=0.9, hallucination=0.0)))
    cand.write_text(json.dumps(_result(faithfulness=0.5, recall_at_20=0.9, hallucination=0.0)))
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/gate.py",
            "--baseline",
            str(base),
            "--candidate",
            str(cand),
            "--config",
            "evals.yaml",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "FAIL" in proc.stdout


def test_cohen_kappa_known_values() -> None:
    assert cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0
    # classic textbook example: 20 agree-yes, 5 yes/no, 10 no/yes, 15 agree-no -> kappa = 0.4
    a = [True] * 25 + [False] * 25
    b = [True] * 20 + [False] * 5 + [True] * 10 + [False] * 15
    assert cohen_kappa(a, b) == pytest.approx(0.4)
    assert cohen_kappa([], []) == 0.0
    assert cohen_kappa([True, True], [True, True]) == 1.0
    with pytest.raises(ValueError):
        cohen_kappa([True], [True, False])
    assert agreement([True, False], [True, True]) == 0.5


def test_length_bias_and_position_swap() -> None:
    bias = length_bias([True, True, False, False], [100, 120, 20, 30])
    assert bias["mean_length_pass"] == 110.0 and bias["mean_length_fail"] == 25.0
    assert bias["point_biserial"] > 0.5
    assert length_bias([True, True], [10, 20])["point_biserial"] == 0.0
    rows = [
        {
            "question": "How long does the canary receive traffic?",
            "answer": "The canary receives 5% of traffic for ten minutes.",
            "context": ["Cats purr.", "The canary receives 5% of traffic for ten minutes."],
            "expected_answer": None,
        }
    ]
    assert position_swap_consistency(LexicalJudge(), "faithfulness", rows) == 1.0
    assert position_swap_consistency(LexicalJudge(), "faithfulness", []) == 0.0
