"""Calibrate the judge against hand labels in evals/human_labels.jsonl.

Reports Cohen's kappa and raw agreement between judge verdicts and human labels (rows with
``human_pass`` filled in), a position-swap consistency check (does reversing the context order
change the verdict?) and a length-bias check (does the judge favour long answers?).

    uv run python scripts/calibrate_judge.py --out reports/judge_calibration.md
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from docs_rag.evals.calibration import (
    agreement,
    cohen_kappa,
    length_bias,
    position_swap_consistency,
)
from docs_rag.evals.judge import get_judge
from docs_rag.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, default=Path("evals/human_labels.jsonl"))
    parser.add_argument("--criterion", default="faithfulness")
    parser.add_argument("--out", type=Path, default=Path("reports/judge_calibration.md"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    settings = get_settings()
    judge = get_judge(settings)
    rows = [
        json.loads(line)
        for line in args.labels.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [r for r in rows if not r.get("refused")]
    verdicts: dict[str, bool] = {}
    for row in rows:
        inp = {"question": row["question"]}
        out = {"answer": row["answer"], "context": row.get("context", [])}
        ref = {"answer": row["expected_answer"]} if row.get("expected_answer") else None
        verdicts[row["id"]] = bool(judge.judge(args.criterion, inp, out, ref)["pass"])

    labelled = [r for r in rows if r.get("human_pass") is not None]
    human = [bool(r["human_pass"]) for r in labelled]
    machine = [verdicts[r["id"]] for r in labelled]
    kappa = cohen_kappa(human, machine) if labelled else None
    agree = agreement(human, machine) if labelled else None
    swap = position_swap_consistency(judge, args.criterion, rows)
    bias = length_bias([verdicts[r["id"]] for r in rows], [len(r["answer"]) for r in rows])

    disagreements = [r for r, h, m in zip(labelled, human, machine, strict=True) if h != m]
    kappa_text = "n/a - no labels yet" if kappa is None else f"{kappa:.3f}"
    agree_text = "n/a" if agree is None else f"{agree:.3f}"
    lines = [
        "# Judge calibration",
        "",
        f"Generated {datetime.now(UTC).isoformat(timespec='seconds')} by "
        f"`scripts/calibrate_judge.py` (judge: **{judge.name}**, criterion: `{args.criterion}`, "
        f"provider: {settings.resolved_llm_provider()}).",
        "",
        "| check | value | n |",
        "|---|---|---|",
        f"| Cohen's kappa (judge vs human) | {kappa_text} | {len(labelled)} |",
        f"| raw agreement | {agree_text} | {len(labelled)} |",
        f"| position-swap consistency | {swap:.3f} | {len(rows)} |",
        f"| mean answer length, judge PASS / FAIL | {bias['mean_length_pass']} / "
        f"{bias['mean_length_fail']} | {len(rows)} |",
        f"| length bias (point-biserial r) | {bias['point_biserial']:+.3f} | {len(rows)} |",
        "",
        "Interpretation: kappa above 0.6 is substantial agreement, 0.4-0.6 moderate, below 0.4 the "
        "judge should not be trusted for this criterion. Position-swap consistency should be close "
        "to 1.0. A length-bias correlation above +0.3 means the judge rewards verbosity.",
    ]
    if not labelled:
        lines += [
            "",
            f"No human labels yet: fill in `human_pass` (true/false) in `{args.labels}` for the "
            "rows marked for verification, then re-run this script.",
        ]
    if disagreements:
        lines += ["", "## Disagreements", ""]
        for r in disagreements:
            lines.append(
                f"- `{r['id']}` human={r['human_pass']} judge={verdicts[r['id']]}: "
                f"{r['question']} -> {r['answer'][:140]!r}"
            )
    report = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
