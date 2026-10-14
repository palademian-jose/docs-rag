"""Calibrate the judge against hand labels in evals/human_labels.jsonl.

For every criterion that has human labels (``labels: {criterion: true|false}``) the script
reports Cohen's kappa and raw agreement between judge verdicts and the humans, a position-swap
consistency check (does reversing the context order change the verdict?) and a length-bias
check (does the judge favour long answers?).

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
from docs_rag.evals.judge import Judge, get_judge
from docs_rag.settings import get_settings


def verdict(judge: Judge, criterion: str, row: dict) -> bool:
    inp = {"question": row["question"]}
    out = {"answer": row["answer"], "context": row.get("context", [])}
    ref = {"answer": row["expected_answer"]} if row.get("expected_answer") else None
    return bool(judge.judge(criterion, inp, out, ref)["pass"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, default=Path("evals/human_labels.jsonl"))
    parser.add_argument(
        "--criteria", default="faithfulness,answer_relevance", help="comma-separated"
    )
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
    criteria = [c.strip() for c in args.criteria.split(",") if c.strip()]

    lines = [
        "# Judge calibration",
        "",
        f"Generated {datetime.now(UTC).isoformat(timespec='seconds')} by "
        f"`scripts/calibrate_judge.py` (judge: **{judge.name}**, provider: "
        f"{settings.resolved_llm_provider()}, {len(rows)} answered rows in `{args.labels}`).",
        "",
        "| criterion | kappa | agreement | labelled n | position-swap consistency | "
        "mean len PASS / FAIL | length bias r |",
        "|---|---|---|---|---|---|---|",
    ]
    disagreements: list[str] = []
    for criterion in criteria:
        verdicts = {r["id"]: verdict(judge, criterion, r) for r in rows}
        labelled = [r for r in rows if r.get("labels", {}).get(criterion) is not None]
        human = [bool(r["labels"][criterion]) for r in labelled]
        machine = [verdicts[r["id"]] for r in labelled]
        kappa = f"{cohen_kappa(human, machine):.3f}" if labelled else "n/a"
        agree = f"{agreement(human, machine):.3f}" if labelled else "n/a"
        swap = position_swap_consistency(judge, criterion, rows)
        bias = length_bias([verdicts[r["id"]] for r in rows], [len(r["answer"]) for r in rows])
        lines.append(
            f"| {criterion} | {kappa} | {agree} | {len(labelled)} | {swap:.3f} | "
            f"{bias['mean_length_pass']} / {bias['mean_length_fail']} | "
            f"{bias['point_biserial']:+.3f} |"
        )
        for r, h, m in zip(labelled, human, machine, strict=True):
            if h != m:
                disagreements.append(
                    f"- `{r['id']}` ({criterion}) human={h} judge={m}: {r['question']} -> "
                    f"{r['answer'][:140]!r}"
                )

    lines += [
        "",
        "Interpretation: kappa above 0.6 is substantial agreement, 0.4-0.6 moderate, below 0.4 "
        "the judge should not be trusted for that criterion. Position-swap consistency should be "
        "close to 1.0. A length-bias correlation above +0.3 means the judge rewards verbosity. "
        "Kappa is undefined when every label is identical; it is reported as 1.0 only when the "
        "judge also agrees on every row.",
    ]
    if not any(r.get("labels", {}).get(c) is not None for r in rows for c in criteria):
        lines += [
            "",
            f"No human labels yet: fill in `labels.<criterion>` (true/false) in `{args.labels}` "
            "for the rows marked for verification, then re-run this script.",
        ]
    if disagreements:
        lines += ["", "## Disagreements", "", *disagreements]
    report = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8", newline="\n")
    print(report)


if __name__ == "__main__":
    main()
