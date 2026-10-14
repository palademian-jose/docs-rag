from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from evalkit.gate import evaluate_gate, load_gate_config
from evalkit.io import load_eval_result, write_eval_result
from evalkit.types import EvalResult

from docs_rag.evals.calibration import (
    agreement,
    cohen_kappa,
    length_bias,
    position_swap_consistency,
)
from docs_rag.evals.judge import LexicalJudge

BASELINE = Path("reports/baseline.json")


def _result(base: dict, **metrics: float) -> EvalResult:
    return EvalResult(run_id="candidate", metrics={**base["metrics"], **metrics})


def _baseline() -> EvalResult:
    return load_eval_result(BASELINE)


def test_evals_yaml_is_an_evalkit_gate_config() -> None:
    cfg = load_gate_config(Path("evals.yaml"))  # extra="forbid": a stale `max_rise` would raise
    assert {"faithfulness", "recall_at_20", "hallucination", "task_success"} <= set(cfg.metrics)
    assert cfg.metrics["hallucination"].max_increase == 0.05
    baseline = _baseline()
    assert set(cfg.metrics) <= set(baseline.metrics)


def test_committed_baseline_passes_its_own_gate() -> None:
    baseline = _baseline()
    report = evaluate_gate(baseline, baseline, load_gate_config(Path("evals.yaml")))
    assert report.ok, report.to_markdown()


def test_gate_fails_on_drop_min_and_rise() -> None:
    cfg = load_gate_config(Path("evals.yaml"))
    baseline = _baseline()
    candidate = _result(
        baseline.model_dump(), faithfulness=0.5, recall_at_20=0.7, hallucination=0.3
    )
    report = evaluate_gate(baseline, candidate, cfg)
    failed = {r.metric: r.reason for r in report.violations}
    assert set(failed) == {"faithfulness", "recall_at_20", "hallucination"}
    assert "dropped" in failed["faithfulness"] and "< min" in failed["recall_at_20"]
    assert "> max" in failed["hallucination"] and "rose" in failed["hallucination"]


def test_evalkit_gate_cli_exits_1_on_regression(tmp_path: Path) -> None:
    baseline = _baseline()
    bad = tmp_path / "bad.json"
    write_eval_result(bad, _result(baseline.model_dump(), faithfulness=0.5))
    cmd = [sys.executable, "-m", "evalkit.cli", "gate", "--baseline", str(BASELINE)]
    cmd += ["--config", "evals.yaml"]
    proc = subprocess.run([*cmd, "--candidate", str(bad)], capture_output=True, text=True)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "GATE FAILED" in proc.stdout and "faithfulness" in proc.stdout
    ok = subprocess.run([*cmd, "--candidate", str(BASELINE)], capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "GATE PASSED" in ok.stdout


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
