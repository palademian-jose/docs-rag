"""Regression gate: compare a candidate eval result against a baseline using evals.yaml.

Same CLI shape as ``evalkit gate --baseline ... --candidate ... --config evals.yaml``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

HIGHER_IS_BETTER_DEFAULT = True


@dataclass
class GateRow:
    metric: str
    baseline: float | None
    candidate: float | None
    min_value: float | None
    max_drop: float | None
    max_value: float | None
    max_rise: float | None
    ok: bool
    note: str


def load_result(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_gate_config(path: Path) -> dict[str, dict[str, float]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return dict(data.get("metrics", {}))


def evaluate_gate(
    baseline: dict[str, Any] | None,
    candidate: dict[str, Any],
    config: dict[str, dict[str, float]],
) -> tuple[bool, list[GateRow]]:
    rows: list[GateRow] = []
    base_metrics = (baseline or {}).get("metrics", {})
    cand_metrics = candidate.get("metrics", {})
    all_ok = True
    for metric, rule in config.items():
        b = base_metrics.get(metric)
        c = cand_metrics.get(metric)
        min_v = rule.get("min")
        max_v = rule.get("max")
        max_drop = rule.get("max_drop")
        max_rise = rule.get("max_rise")
        notes: list[str] = []
        ok = True
        if c is None:
            ok = False
            notes.append("missing in candidate")
        else:
            if min_v is not None and c < min_v:
                ok = False
                notes.append(f"below min {min_v}")
            if max_v is not None and c > max_v:
                ok = False
                notes.append(f"above max {max_v}")
            if b is not None:
                if max_drop is not None and (b - c) > max_drop:
                    ok = False
                    notes.append(f"dropped {b - c:.4f} > {max_drop}")
                if max_rise is not None and (c - b) > max_rise:
                    ok = False
                    notes.append(f"rose {c - b:.4f} > {max_rise}")
            elif max_drop is not None or max_rise is not None:
                notes.append("no baseline value; delta check skipped")
        all_ok = all_ok and ok
        rows.append(GateRow(metric, b, c, min_v, max_drop, max_v, max_rise, ok, "; ".join(notes)))
    return all_ok, rows


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.4f}"


def render_markdown(rows: list[GateRow], *, ok: bool) -> str:
    lines = [
        "| metric | baseline | candidate | delta | rule | status |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        delta = (
            "-" if r.baseline is None or r.candidate is None else f"{r.candidate - r.baseline:+.4f}"
        )
        rule_parts = []
        if r.min_value is not None:
            rule_parts.append(f"min {r.min_value}")
        if r.max_value is not None:
            rule_parts.append(f"max {r.max_value}")
        if r.max_drop is not None:
            rule_parts.append(f"max_drop {r.max_drop}")
        if r.max_rise is not None:
            rule_parts.append(f"max_rise {r.max_rise}")
        status = "PASS" if r.ok else f"FAIL ({r.note})" if r.note else "FAIL"
        if r.ok and r.note:
            status = f"PASS ({r.note})"
        lines.append(
            f"| {r.metric} | {_fmt(r.baseline)} | {_fmt(r.candidate)} | {delta} | "
            f"{', '.join(rule_parts) or '-'} | {status} |"
        )
    lines.append("")
    lines.append(f"**Gate: {'PASS' if ok else 'FAIL'}**")
    return "\n".join(lines)
