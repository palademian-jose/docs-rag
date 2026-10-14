"""Run a golden set through a pipeline and produce an eval result (PLAN.md shared contract 3)."""

from __future__ import annotations

import subprocess
import uuid
from datetime import UTC, datetime
from typing import Any

from docs_rag.evals.golden import GoldenCase, is_relevant
from docs_rag.evals.judge import Judge
from docs_rag.evals.metrics import (
    hit_at_k,
    mean,
    mrr,
    ndcg_at_k,
    percentile,
    precision_at_k,
    recall_at_k,
)
from docs_rag.pipeline import RAGPipeline
from docs_rag.pricing import PriceBook

K_VALUES = (5, 20, 50)


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def score_case(
    pipeline: RAGPipeline, case: GoldenCase, judge: Judge, *, k_values: tuple[int, ...] = K_VALUES
) -> dict[str, Any]:
    result = pipeline.ask(case.question)
    exp = case.expected
    scores: dict[str, float] = {}
    by_id = pipeline.index.by_id

    if not exp.refuse:
        # Effective ranking: what the model saw (reranked top-k) first, then the remaining
        # candidates in retrieval order. Without a reranker this is just the retrieval order.
        seen = set(result.context_ids)
        ranking = result.context_ids + [c for c in result.retrieved_ids if c not in seen]
        flags = [is_relevant(by_id[cid], exp) for cid in ranking if cid in by_id]
        n_relevant = sum(1 for c in pipeline.index.chunks if is_relevant(c, exp))
        for k in k_values:
            scores[f"recall_at_{k}"] = recall_at_k(flags, k, n_relevant)
            scores[f"hit_at_{k}"] = hit_at_k(flags, k)
        scores["precision_at_5"] = precision_at_k(flags, 5)
        scores["mrr"] = mrr(flags)
        scores["ndcg_at_10"] = ndcg_at_k(flags, 10, n_relevant)
        ctx_flags = [is_relevant(by_id[cid], exp) for cid in result.context_ids if cid in by_id]
        scores["context_precision"] = mean([1.0 if f else 0.0 for f in ctx_flags])

    scores["refused"] = 1.0 if result.refused else 0.0
    scores["refusal_correct"] = 1.0 if result.refused == exp.refuse else 0.0

    if not result.refused:
        cited = [by_id[c.chunk_id].text for c in result.citations if c.chunk_id in by_id]
        output = {"answer": result.answer, "context": cited, "refused": False}
        reference = {"answer": exp.answer} if exp.answer else None
        faith = judge.judge("faithfulness", {"question": case.question}, output, reference)
        rel = judge.judge("answer_relevance", {"question": case.question}, output, reference)
        scores["faithfulness"] = 1.0 if faith["pass"] else 0.0
        scores["answer_relevance"] = 1.0 if rel["pass"] else 0.0
        scores["hallucination"] = 1.0 if (exp.refuse or not faith["pass"]) else 0.0
        scores["citation_count"] = float(len(result.citations))
        judge_reasons = {"faithfulness": faith["reason"], "answer_relevance": rel["reason"]}
    else:
        judge_reasons = {}

    if exp.refuse:
        passed = result.refused
    else:
        passed = (
            not result.refused
            and scores.get("faithfulness", 0.0) == 1.0
            and scores.get("hit_at_20", 0.0) == 1.0
        )
    return {
        "id": case.id,
        "scores": scores,
        "passed": passed,
        "latency_ms": round(result.latency_ms, 2),
        "cost_usd": result.cost_usd,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "answer": result.answer,
        "refused": result.refused,
        "refusal_reason": result.refusal_reason,
        "citations": [c.model_dump() for c in result.citations],
        "judge": judge_reasons,
        "tags": case.tags,
        "source": case.source,
        "failure_mode": case.failure_mode,
    }


def aggregate(cases: list[dict[str, Any]]) -> dict[str, float]:
    metric_names = sorted({name for c in cases for name in c["scores"]})
    metrics: dict[str, float] = {}
    for name in metric_names:
        values = [c["scores"][name] for c in cases if name in c["scores"]]
        if values:
            metrics[name] = round(mean(values), 4)
    in_corpus = [c for c in cases if c["failure_mode"] != "refusal_miss"]
    off_corpus = [c for c in cases if c["failure_mode"] == "refusal_miss"]
    if in_corpus:
        metrics["false_refusal_rate"] = round(mean([c["scores"]["refused"] for c in in_corpus]), 4)
    if off_corpus:
        metrics["refusal_recall"] = round(mean([c["scores"]["refused"] for c in off_corpus]), 4)
    metrics["task_success"] = round(mean([1.0 if c["passed"] else 0.0 for c in cases]), 4)
    latencies = [c["latency_ms"] for c in cases]
    metrics["p50_latency_ms"] = round(percentile(latencies, 50), 2)
    metrics["p95_latency_ms"] = round(percentile(latencies, 95), 2)
    total_cost = sum(c["cost_usd"] for c in cases)
    metrics["cost_per_1k_queries_usd"] = round(total_cost / len(cases) * 1000, 4) if cases else 0.0
    metrics["avg_input_tokens"] = round(mean([c["input_tokens"] for c in cases]), 1)
    metrics["avg_output_tokens"] = round(mean([c["output_tokens"] for c in cases]), 1)
    return metrics


def run_eval(
    pipeline: RAGPipeline,
    cases: list[GoldenCase],
    judge: Judge,
    *,
    run_name: str,
    provider: str,
    model: str,
    config: dict[str, Any] | None = None,
    k_values: tuple[int, ...] = K_VALUES,
    pricing: PriceBook | None = None,
    price_model: str | None = None,
) -> dict[str, Any]:
    scored = [score_case(pipeline, case, judge, k_values=k_values) for case in cases]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    metrics = aggregate(scored)
    by_source = {
        source: aggregate([c for c in scored if c["source"] == source])
        for source in sorted({c["source"] for c in scored})
    }
    if pricing is not None and price_model:
        metrics["projected_cost_per_1k_usd"] = project_cost(scored, pricing, price_model)
        for source, group in by_source.items():
            group["projected_cost_per_1k_usd"] = project_cost(
                [c for c in scored if c["source"] == source], pricing, price_model
            )
    return {
        "run_id": f"{run_name}-{stamp}-{uuid.uuid4().hex[:6]}",
        "run_name": run_name,
        "commit": git_commit(),
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "provider": provider,
        "model": model,
        "judge": judge.name,
        "n_cases": len(scored),
        "config": config or {},
        "price_model": price_model,
        "metrics": metrics,
        "metrics_by_source": by_source,
        "cases": scored,
    }


def project_cost(cases: list[dict[str, Any]], pricing: PriceBook, model: str) -> float:
    """USD per 1k queries if the observed token counts were billed at ``model`` list price."""
    if not cases:
        return 0.0
    total = sum(pricing.token_cost(model, c["input_tokens"], c["output_tokens"]) for c in cases)
    return round(total / len(cases) * 1000, 4)
