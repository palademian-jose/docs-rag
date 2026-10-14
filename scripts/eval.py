"""Evaluate pipeline variants on the golden set and write reports/ (PLAN.md eval result format).

Variants (--mode):
  naive     dense top-k, no reranker                       (v0)
  hybrid    BM25 + dense fused with RRF, no reranker       (v2)
  reranked  hybrid recall@50 -> rerank -> top-5            (v3)
  final     reranked + answer cache + tracing              (v5)
  all       run every variant and write reports/results.md
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
from pathlib import Path

from docs_rag.bootstrap import build_pipeline
from docs_rag.evals.golden import load_golden, resolve_answer_lines
from docs_rag.evals.judge import get_judge
from docs_rag.evals.runner import run_eval
from docs_rag.ingest.index import load_or_build_index
from docs_rag.settings import Settings, get_settings

VARIANTS: dict[str, dict] = {
    "naive": {"retrieval_mode": "dense", "reranker": "none", "cache": False},
    "hybrid": {"retrieval_mode": "hybrid", "reranker": "none", "cache": False},
    "reranked": {"retrieval_mode": "hybrid", "reranker": None, "cache": False},
    "final": {"retrieval_mode": "hybrid", "reranker": None, "cache": True},
}

TABLE_COLUMNS = [
    ("recall_at_5", "recall@5"),
    ("recall_at_20", "recall@20"),
    ("precision_at_5", "precision@5"),
    ("mrr", "MRR"),
    ("faithfulness", "faithfulness"),
    ("hallucination", "halluc. rate"),
    ("refusal_recall", "refusal recall"),
    ("false_refusal_rate", "false refusal"),
    ("p95_latency_ms", "p95 ms"),
    ("projected_cost_per_1k_usd", "$/1k (projected)"),
]


def _table(results: dict[str, dict], metrics_key: str, source: str | None = None) -> str:
    header = "| variant | " + " | ".join(label for _, label in TABLE_COLUMNS) + " |"
    sep = "|---|" + "---|" * len(TABLE_COLUMNS)
    rows = [header, sep]
    for name, res in results.items():
        m = res[metrics_key] if source is None else res[metrics_key].get(source, {})
        cells = []
        for key, _ in TABLE_COLUMNS:
            v = m.get(key)
            cells.append("-" if v is None else (f"{v:.0f}" if key.endswith("_ms") else f"{v:.3f}"))
        rows.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def results_table(results: dict[str, dict], settings: Settings) -> str:
    provider = settings.resolved_llm_provider()
    first = next(iter(results.values()))
    sources = sorted(first.get("metrics_by_source", {}))
    parts = [f"### All cases ({first['n_cases']})", "", _table(results, "metrics"), ""]
    for source in sources:
        n = sum(1 for c in first["cases"] if c["source"] == source)
        parts += [
            f"### Source: {source} ({n} cases)",
            "",
            _table(results, "metrics_by_source", source),
            "",
        ]
    note = (
        f"Provider: **{provider}**"
        + (
            " (deterministic fake LLM, hashed-bag-of-words embeddings, lexical judge). "
            "These numbers describe the plumbing, not a real model: set OPENROUTER_API_KEY "
            "and run `make eval` for real numbers."
            if provider == "fake"
            else f", model `{settings.llm_model}`, judge `{settings.judge_model}`."
        )
        + "\nSynthetic questions are templated from the chunk they target and therefore "
        "overstate recall; the `human` rows are the honest ones. `$/1k (projected)` prices the "
        "observed token counts at the configured model's list price in pricing.json."
    )
    return "\n".join(parts) + note + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mode", choices=[*VARIANTS, "all"], default="all")
    parser.add_argument("--golden", type=Path, nargs="*", default=None)
    parser.add_argument("--limit", type=int, default=None, help="use only the first N cases")
    parser.add_argument("--out", type=Path, default=Path("reports"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    settings = get_settings()
    golden_paths = args.golden or sorted(Path("evals/golden").glob("*.jsonl"))
    cases = resolve_answer_lines(load_golden(golden_paths), Path(settings.corpus_path))
    if args.limit:
        in_corpus = [c for c in cases if not c.expected.refuse][: args.limit]
        refusals = [c for c in cases if c.expected.refuse][: max(2, args.limit // 5)]
        cases = in_corpus + refusals
    if not cases:
        raise SystemExit("no golden cases found; run scripts/build_eval_set.py first")

    index = load_or_build_index(settings)
    judge = get_judge(settings)
    args.out.mkdir(parents=True, exist_ok=True)
    modes = list(VARIANTS) if args.mode == "all" else [args.mode]
    results: dict[str, dict] = {}
    for mode in modes:
        variant = VARIANTS[mode]
        pipeline = build_pipeline(
            settings,
            index=index,
            retrieval_mode=variant["retrieval_mode"],
            reranker=variant["reranker"],
            cache_enabled=variant["cache"],
        )
        res = run_eval(
            pipeline,
            cases,
            judge,
            run_name=mode,
            provider=settings.resolved_llm_provider(),
            model=settings.llm_model
            if settings.resolved_llm_provider() != "fake"
            else pipeline.llm.model,
            config={
                **variant,
                "reranker": pipeline.reranker.name if pipeline.reranker else "none",
                "chunk_size": index.chunk_size,
                "chunk_overlap": index.chunk_overlap,
                "n_chunks": len(index.chunks),
                "top_k": pipeline.config.top_k,
                "candidates": pipeline.config.candidates,
                "embedding_model": index.embedder.model_name,
            },
        )
        results[mode] = res
        path = args.out / f"eval-{res['run_id']}.json"
        path.write_text(json.dumps(res, indent=2), encoding="utf-8")
        shutil.copyfile(path, args.out / f"eval-{mode}.json")
        m = res["metrics"]
        print(
            f"{mode:9s} recall@20={m.get('recall_at_20', 0):.3f} "
            f"precision@5={m.get('precision_at_5', 0):.3f} "
            f"faithfulness={m.get('faithfulness', 0):.3f} success={m['task_success']:.3f} "
            f"p95={m['p95_latency_ms']:.0f}ms"
        )
    final_name = modes[-1]
    shutil.copyfile(args.out / f"eval-{final_name}.json", args.out / "eval-latest.json")
    if args.mode == "all":
        table = results_table(results, settings)
        (args.out / "results.md").write_text(table, encoding="utf-8")
        print("\n" + table)


if __name__ == "__main__":
    main()
