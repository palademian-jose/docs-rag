"""Sweep chunk size and overlap, re-indexing for each, and write reports/chunk_sweep.md.

Relevance in the golden set is defined on source line spans, so the same questions score
every chunking configuration fairly. Two tables are written: all in-corpus questions and the
hand-written subset (synthetic questions are templated from their target chunk and saturate
recall on a corpus this small).
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

from docs_rag.bootstrap import build_pipeline
from docs_rag.embeddings import get_embedder
from docs_rag.evals.golden import load_golden, resolve_answer_lines
from docs_rag.evals.judge import get_judge
from docs_rag.evals.metrics import mean
from docs_rag.evals.runner import run_eval
from docs_rag.ingest.chunking import count_tokens
from docs_rag.ingest.index import build_index
from docs_rag.settings import get_settings
from docs_rag.vectorstore.memory import MemoryVectorStore

COLUMNS = [
    ("hit_at_5", "hit@5"),
    ("recall_at_5", "recall@5"),
    ("recall_at_20", "recall@20"),
    ("precision_at_5", "precision@5"),
    ("mrr", "MRR"),
    ("ndcg_at_10", "nDCG@10"),
    ("context_precision", "context precision"),
    ("faithfulness", "faithfulness"),
    ("p95_latency_ms", "p95 ms"),
]


def table(rows: list[dict], metrics_key: str, source: str | None) -> str:
    header = "| size | overlap | chunks | avg tokens | " + " | ".join(c[1] for c in COLUMNS) + " |"
    sep = "|---|---|---|---|" + "---|" * len(COLUMNS)
    out = [header, sep]
    for r in rows:
        m = r[metrics_key] if source is None else r[metrics_key].get(source, {})
        cells = []
        for key, _ in COLUMNS:
            v = m.get(key)
            cells.append("-" if v is None else (f"{v:.0f}" if key.endswith("_ms") else f"{v:.3f}"))
        out.append(
            f"| {r['size']} | {r['overlap']} | {r['chunks']} | {r['avg_tokens']} | "
            + " | ".join(cells)
            + " |"
        )
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="128,256,512", help="comma-separated chunk sizes")
    parser.add_argument("--overlaps", default="0,32", help="comma-separated overlaps")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", type=Path, default=Path("reports/chunk_sweep.md"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    settings = get_settings()
    golden = sorted(Path("evals/golden").glob("*.jsonl"))
    cases = resolve_answer_lines(load_golden(golden), Path(settings.corpus_path))
    cases = [c for c in cases if not c.expected.refuse]
    if args.limit:
        cases = cases[: args.limit]
    judge = get_judge(settings)
    embedder = get_embedder(settings)
    provider = settings.resolved_llm_provider()

    rows: list[dict] = []
    for size in [int(s) for s in args.sizes.split(",")]:
        for overlap in [int(o) for o in args.overlaps.split(",")]:
            if overlap >= size:
                continue
            index = build_index(
                settings,
                embedder=embedder,
                store=MemoryVectorStore(embedder.dim),
                chunk_size=size,
                chunk_overlap=overlap,
            )
            pipeline = build_pipeline(settings, index=index, retrieval_mode="hybrid")
            res = run_eval(
                pipeline,
                cases,
                judge,
                run_name=f"sweep-{size}-{overlap}",
                provider=provider,
                model=getattr(pipeline.llm, "model", settings.llm_model),
            )
            rows.append(
                {
                    "size": size,
                    "overlap": overlap,
                    "chunks": len(index.chunks),
                    "avg_tokens": round(mean([count_tokens(c.text) for c in index.chunks]), 1),
                    "metrics": res["metrics"],
                    "metrics_by_source": res["metrics_by_source"],
                }
            )
            m = res["metrics"]
            print(
                f"size={size:4d} overlap={overlap:3d} chunks={len(index.chunks):4d} "
                f"hit@5={m['hit_at_5']:.3f} precision@5={m['precision_at_5']:.3f} "
                f"mrr={m['mrr']:.3f} faithfulness={m.get('faithfulness', 0):.3f}"
            )

    n_human = sum(1 for c in cases if c.source == "human")
    lines = [
        "# Chunk size sweep",
        "",
        f"Generated {datetime.now(UTC).isoformat(timespec='seconds')} by "
        f"`scripts/sweep_chunks.py` (provider: **{provider}**, hybrid retrieval + "
        f"{settings.reranker} reranker, {len(cases)} questions of which {n_human} hand-written).",
        "",
        "Sizes are word tokens (about 0.75 LLM tokens). A retrieved chunk counts as relevant when "
        "it contains the golden answer line, so every configuration is scored by the same "
        "questions. With overlap 0 exactly one chunk is relevant per question, which caps "
        "precision@5 at 0.2 and context precision at 0.2; with overlap the answer line can fall "
        "in two chunks. Compare hit@5, MRR and nDCG across rows, not precision in isolation.",
        "",
        f"## All in-corpus questions ({len(cases)})",
        "",
        table(rows, "metrics", None),
        "",
        f"## Hand-written questions ({n_human})",
        "",
        table(rows, "metrics_by_source", "human"),
    ]
    if provider == "fake":
        lines += [
            "",
            "Fake provider: hashed bag-of-words embeddings, BM25, lexical reranker and an "
            "extractive fake LLM. Synthetic questions are templated from their target chunk, so "
            "they saturate recall on a corpus this small; absolute values are not comparable to "
            "a real model. Re-run with a real key for numbers that can drive the choice.",
        ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
