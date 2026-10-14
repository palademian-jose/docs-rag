"""Replay the golden set under four serving configurations and write each run's spans to its own
directory, so `llmops before-after` can build a real before/after table from them.

    uv run python scripts/trace_scenarios.py       # -> traces/scenarios/<scenario>/spans.jsonl
    uv run llmops before-after --dirs "traces/scenarios/*" --md reports/before_after.md

Scenarios (cumulative, like llm-evalops' synthetic ladder):

  baseline        no answer cache; the golden questions once
  exact_cache     exact answer cache; the questions twice, so the second pass hits
  semantic_cache  exact + semantic cache (llmops.cache.SemanticCache, fake embedding backend); the
                  questions, then lightly reworded versions of them (some are near-duplicates the
                  semantic layer catches, some are not)
  cheaper_model   semantic_cache with LLM_MODEL switched to CHEAP_MODEL (claude-haiku-4.5)

The provider is the deterministic FAKE one: it has no real latency and no real bill. To get a
cost column anyway, the fake client reports the model it is "billed as" (LLM_MODEL, or CHEAP_MODEL
for cheaper_model) and the fake reranker is billed as Cohere `rerank-v3.5`; llmops prices the
observed token counts at those models' list prices (llmops/pricing.json). Treat the cost column as
PROJECTED, and the latency columns as pipeline compute only. Cache hit rates come from the replay
design above, not from real traffic.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from docs_rag.bootstrap import build_pipeline
from docs_rag.cache import MemoryAnswerCache, SemanticAnswerCache
from docs_rag.evals.golden import load_golden
from docs_rag.ingest.index import load_or_build_index
from docs_rag.limits import DailyCostCap
from docs_rag.llm import FakeLLMClient
from docs_rag.rerank.fake import FakeReranker
from docs_rag.settings import Settings, get_settings
from docs_rag.tracing import make_tracer, read_spans

SCENARIOS = ("baseline", "exact_cache", "semantic_cache", "cheaper_model")
RERANK_BILLED_AS = "rerank-v3.5"
_ARTICLE = re.compile(r"\b(the|a|an)\s+", re.IGNORECASE)


class _BilledReranker(FakeReranker):
    """The lexical fake reranker, reported (and therefore priced) as Cohere rerank-v3.5."""

    model_name = RERANK_BILLED_AS


def reword(question: str, i: int) -> str:
    """Deterministic light rewording. Cycles through four transforms so that some variants stay
    above the semantic threshold and some fall below it."""
    q = question.strip()
    kind = i % 4
    if kind == 0:
        return q.rstrip("?") + " please?"
    if kind == 1:
        return "Tell me: " + q
    if kind == 2:
        return _ARTICLE.sub("", q)
    return "Can you tell me " + q[:1].lower() + q[1:]


def _passes(name: str, questions: list[str]) -> list[list[str]]:
    if name == "baseline":
        return [questions]
    if name == "exact_cache":
        return [questions, questions]
    return [questions, [reword(q, i) for i, q in enumerate(questions)]]


def run_scenario(
    name: str, questions: list[str], settings: Settings, index: Any, out_dir: Path, threshold: float
) -> dict[str, Any]:
    model = settings.cheap_model if name == "cheaper_model" else settings.llm_model
    settings = settings.model_copy(update={"llm_model": model, "cache_enabled": name != "baseline"})
    spans_path = out_dir / name / "spans.jsonl"
    spans_path.parent.mkdir(parents=True, exist_ok=True)
    for stale in (spans_path, spans_path.with_name(spans_path.name + ".lock")):
        stale.unlink(missing_ok=True)
    tracer = make_tracer(spans_path)
    semantic = (
        SemanticAnswerCache(threshold, tracer=tracer)
        if name in ("semantic_cache", "cheaper_model")
        else None
    )
    pipeline = build_pipeline(
        settings,
        index=index,
        llm=FakeLLMClient(model=model),
        tracer=tracer,
        cache=MemoryAnswerCache() if name != "baseline" else None,
        semantic_cache=semantic if semantic is not None else False,
        cost_cap=DailyCostCap(1e9),
    )
    if pipeline.reranker is not None:
        pipeline.reranker = _BilledReranker()
    results = [
        pipeline.ask(q, user_id=f"u{i % 20:02d}")
        for p in _passes(name, questions)
        for i, q in enumerate(p)
    ]
    tracer.sink.close()  # type: ignore[attr-defined]

    spans = read_spans(spans_path)
    sem_hits = [s for s in spans if s["name"] == "cache.semantic" and s["cache_hit"]]
    return {
        "scenario": name,
        "model": model,
        "requests": len(results),
        "exact_hits": sum(1 for r in results if r.cache_kind == "exact"),
        "semantic_hits": sum(1 for r in results if r.cache_kind == "semantic"),
        "llm_calls": sum(1 for s in spans if s["kind"] == "llm"),
        "refused": sum(1 for r in results if r.refused),
        "cost_usd": round(sum(s["cost_usd"] for s in spans), 6),
        "min_semantic_similarity": min((s["meta"]["similarity"] for s in sem_hits), default=None),
        "spans": len(spans),
    }


def main(argv: list[str] | None = None) -> dict[str, dict[str, Any]]:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, default=Path("traces/scenarios"))
    parser.add_argument("--golden", type=Path, nargs="*", default=None)
    parser.add_argument("--limit", type=int, default=None, help="use only the first N questions")
    parser.add_argument("--threshold", type=float, default=None, help="semantic cache threshold")
    args = parser.parse_args(argv)

    settings = get_settings()
    if settings.resolved_llm_provider() != "fake":
        raise SystemExit("trace_scenarios.py replays with the fake provider: set LLM_PROVIDER=fake")
    paths = args.golden or sorted(Path("evals/golden").glob("*.jsonl"))
    questions = [c.question for c in load_golden(paths)]
    if args.limit:
        questions = questions[: args.limit]
    if not questions:
        raise SystemExit("no golden questions found")
    threshold = args.threshold if args.threshold is not None else settings.semantic_cache_threshold
    index = load_or_build_index(settings)

    stats: dict[str, dict[str, Any]] = {}
    for name in SCENARIOS:
        stats[name] = run_scenario(name, questions, settings, index, args.out, threshold)
        s = stats[name]
        print(
            f"{name:15s} model={s['model']:28s} requests={s['requests']:4d} "
            f"exact_hits={s['exact_hits']:4d} semantic_hits={s['semantic_hits']:4d} "
            f"llm_calls={s['llm_calls']:4d} projected_cost=${s['cost_usd']:.4f}"
        )
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    (args.out / "README.md").write_text(
        "# docs-rag trace scenarios\n\n"
        "Written by `scripts/trace_scenarios.py` with the FAKE provider: spans come from real\n"
        "pipeline runs, but the LLM has no real latency and no real bill. `cost_usd` is\n"
        "projected: observed token counts priced at the list price of the model the fake client\n"
        "reports\n"
        "(LLM_MODEL, or CHEAP_MODEL for cheaper_model) and the reranker billed as Cohere\n"
        "rerank-v3.5. Build the table with\n"
        '`llmops before-after --dirs "traces/scenarios/*" --md reports/before_after.md`.\n',
        encoding="utf-8",
    )
    return stats


if __name__ == "__main__":
    main(sys.argv[1:])
