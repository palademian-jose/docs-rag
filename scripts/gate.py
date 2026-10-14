"""Regression gate with the same CLI shape as `evalkit gate`.

    uv run python scripts/gate.py --baseline reports/baseline.json \
        --candidate reports/eval-latest.json --config evals.yaml

Exits 1 on regression and prints a Markdown table either way.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docs_rag.evals.gate import evaluate_gate, load_gate_config, load_result, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("evals.yaml"))
    parser.add_argument("--out", type=Path, default=None, help="also write the table here")
    args = parser.parse_args()

    baseline = load_result(args.baseline) if args.baseline.exists() else None
    if baseline is None:
        print(f"note: baseline {args.baseline} not found; only absolute thresholds apply")
    candidate = load_result(args.candidate)
    ok, rows = evaluate_gate(baseline, candidate, load_gate_config(args.config))
    table = render_markdown(rows, ok=ok)
    print(table)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(table + "\n", encoding="utf-8", newline="\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
