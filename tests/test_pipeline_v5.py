from __future__ import annotations

from pathlib import Path

import pytest

from docs_rag.bootstrap import build_pipeline
from docs_rag.cache import MemoryAnswerCache
from docs_rag.limits import DailyCostCap
from docs_rag.llm import FakeLLMClient
from docs_rag.pipeline import CostCapError, PipelineConfig, RAGPipeline
from docs_rag.pricing import PriceBook
from docs_rag.rerank.fake import FakeReranker
from docs_rag.retrieval.bm25 import BM25Retriever
from docs_rag.retrieval.dense import DenseRetriever
from docs_rag.retrieval.hybrid import HybridRetriever
from docs_rag.tracing import Tracer, read_spans

PRICES = PriceBook(
    {
        "fake-extractive-v1": {"input_per_m": 3.0, "output_per_m": 15.0},
        "fake-lexical-overlap": {"input_per_m": 0, "output_per_m": 0, "per_call": 0.002},
        "fake-hashed-bow-256": {"input_per_m": 0.13, "output_per_m": 0.0},
    }
)
QUESTION = "How long does the canary receive 5% of traffic?"


def _pipeline(corpus_index, tmp_path: Path, **kwargs) -> RAGPipeline:
    tracer = kwargs.pop("tracer", Tracer(tmp_path / "spans.jsonl"))
    dense = DenseRetriever(corpus_index, tracer=tracer, pricing=PRICES)
    hybrid = HybridRetriever(dense, BM25Retriever(corpus_index.chunks))
    config = kwargs.pop(
        "config", PipelineConfig(top_k=5, candidates=50, refusal_threshold=0.15, cache_enabled=True)
    )
    return RAGPipeline(
        corpus_index,
        FakeLLMClient(),
        hybrid,
        config,
        reranker=FakeReranker(),
        tracer=tracer,
        pricing=PRICES,
        **kwargs,
    )


def test_spans_cover_every_stage_with_cost(corpus_index, tmp_path: Path) -> None:
    pipeline = _pipeline(corpus_index, tmp_path, cache=MemoryAnswerCache())
    result = pipeline.ask(QUESTION)
    spans = read_spans(tmp_path / "spans.jsonl")
    names = [s["name"] for s in spans]
    assert names == ["cache.lookup", "embed.query", "retrieve", "rerank", "generate", "rag.ask"]
    assert len({s["trace_id"] for s in spans}) == 1
    assert spans[0]["trace_id"] == result.trace_id
    root = spans[-1]
    assert root["kind"] == "other" and root["parent_span_id"] is None
    assert all(s["parent_span_id"] is not None for s in spans[:-1])
    gen = next(s for s in spans if s["name"] == "generate")
    assert gen["kind"] == "llm" and gen["input_tokens"] > 0
    expected_gen = PRICES.token_cost(
        "fake-extractive-v1", gen["input_tokens"], gen["output_tokens"]
    )
    assert gen["cost_usd"] == pytest.approx(expected_gen)
    assert gen["meta"]["computed_cost_usd"] == pytest.approx(expected_gen)
    rerank = next(s for s in spans if s["name"] == "rerank")
    assert rerank["cost_usd"] == pytest.approx(0.002)
    assert result.cost_usd == pytest.approx(expected_gen + 0.002)
    assert root["cost_usd"] == pytest.approx(result.cost_usd)
    assert spans[0]["kind"] == "cache" and spans[0]["cache_hit"] is False


def test_cache_hit_skips_model_and_costs_nothing(corpus_index, tmp_path: Path) -> None:
    cache = MemoryAnswerCache()
    pipeline = _pipeline(corpus_index, tmp_path, cache=cache)
    first = pipeline.ask(QUESTION)
    second = pipeline.ask("  how long does the canary receive 5% of traffic ")
    assert not first.cache_hit and second.cache_hit
    assert second.answer == first.answer and second.citations == first.citations
    assert second.cost_usd == 0.0 and second.trace_id != first.trace_id
    assert len(pipeline.llm.calls) == 1
    spans = read_spans(tmp_path / "spans.jsonl")
    assert [s["name"] for s in spans[-2:]] == ["cache.lookup", "rag.ask"]
    assert spans[-2]["cache_hit"] is True and spans[-1]["cache_hit"] is True


def test_cache_key_changes_with_configuration(corpus_index, tmp_path: Path) -> None:
    cache = MemoryAnswerCache()
    a = _pipeline(corpus_index, tmp_path, cache=cache)
    a.ask(QUESTION)
    b = _pipeline(
        corpus_index,
        tmp_path,
        cache=cache,
        config=PipelineConfig(top_k=3, candidates=50, refusal_threshold=0.15, cache_enabled=True),
    )
    assert a.fingerprint != b.fingerprint
    assert not b.ask(QUESTION).cache_hit


def test_cache_disabled_never_touches_cache(corpus_index, tmp_path: Path) -> None:
    cache = MemoryAnswerCache()
    config = PipelineConfig(top_k=5, candidates=50, refusal_threshold=0.15, cache_enabled=False)
    pipeline = _pipeline(corpus_index, tmp_path, cache=cache, config=config)
    pipeline.ask(QUESTION)
    pipeline.ask(QUESTION)
    assert len(cache) == 0 and len(pipeline.llm.calls) == 2


def test_cost_cap_blocks_new_calls_but_serves_cache(corpus_index, tmp_path: Path) -> None:
    cap = DailyCostCap(0.005)
    pipeline = _pipeline(corpus_index, tmp_path, cache=MemoryAnswerCache(), cost_cap=cap)
    first = pipeline.ask(QUESTION)
    assert cap.spent_today == pytest.approx(first.cost_usd)
    cap.record(1.0)
    with pytest.raises(CostCapError):
        pipeline.ask("What is the pull request size limit?")
    assert pipeline.ask(QUESTION).cache_hit, "cached answers stay available under the cap"
    spans = read_spans(tmp_path / "spans.jsonl")
    errored = [s for s in spans if s["status"] == "error"]
    assert errored and errored[0]["error_kind"] == "CostCapError"


def test_build_pipeline_wires_everything(settings) -> None:
    pipeline = build_pipeline(settings)
    assert pipeline.tracer.enabled and pipeline.cache is not None
    assert pipeline.cost_cap is not None and pipeline.reranker is not None
    assert pipeline.retriever.name == "hybrid"
    result = pipeline.ask(QUESTION)
    assert not result.refused and result.cost_usd == 0.0  # fake models are free
    assert settings.trace_path.exists()
    naive = build_pipeline(settings, index=pipeline.index, retrieval_mode="dense", reranker="none")
    assert naive.retriever.name == "dense" and naive.reranker is None
