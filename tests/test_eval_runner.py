from __future__ import annotations

from pathlib import Path

from docs_rag.evals.golden import (
    Expected,
    GoldenCase,
    is_relevant,
    load_golden,
    resolve_answer_lines,
    save_golden,
)
from docs_rag.evals.judge import LexicalJudge
from docs_rag.evals.runner import aggregate, run_eval, score_case
from docs_rag.ingest.chunking import Chunk
from docs_rag.llm import FakeLLMClient
from docs_rag.pipeline import PipelineConfig, RAGPipeline
from docs_rag.rerank.fake import FakeReranker
from docs_rag.retrieval.bm25 import BM25Retriever
from docs_rag.retrieval.dense import DenseRetriever
from docs_rag.retrieval.hybrid import HybridRetriever


def _pipeline(corpus_index) -> RAGPipeline:
    hybrid = HybridRetriever(DenseRetriever(corpus_index), BM25Retriever(corpus_index.chunks))
    config = PipelineConfig(top_k=5, candidates=50, refusal_threshold=0.15)
    return RAGPipeline(corpus_index, FakeLLMClient(), hybrid, config, reranker=FakeReranker())


def test_is_relevant_uses_line_spans() -> None:
    chunk = Chunk("c", "a.md", "A", None, 10, 20, "x", 0)
    assert is_relevant(chunk, Expected(doc_path="a.md", answer_line=15))
    assert not is_relevant(chunk, Expected(doc_path="a.md", answer_line=21))
    assert is_relevant(chunk, Expected(doc_path="a.md", start_line=18, end_line=30))
    assert not is_relevant(chunk, Expected(doc_path="b.md", answer_line=15))
    assert is_relevant(chunk, Expected(doc_path="a.md", chunk_ids=["c"]))
    assert not is_relevant(chunk, Expected(refuse=True, doc_path="a.md", answer_line=15))


def test_golden_roundtrip_and_phrase_resolution(tmp_path: Path, corpus_path: Path) -> None:
    cases = load_golden(Path("evals/golden/handwritten.jsonl"))
    assert len(cases) >= 20
    assert all(c.source == "human" for c in cases)
    resolve_answer_lines(cases, corpus_path)
    for case in cases:
        if not case.expected.refuse:
            assert case.expected.answer_line is not None, case.id
    out = tmp_path / "g.jsonl"
    save_golden(out, cases[:3])
    assert [c.id for c in load_golden(out)] == [c.id for c in cases[:3]]


def test_score_case_in_corpus_and_refusal(corpus_index, corpus_path: Path) -> None:
    pipeline = _pipeline(corpus_index)
    judge = LexicalJudge()
    cases = resolve_answer_lines(load_golden(Path("evals/golden/handwritten.jsonl")), corpus_path)
    canary = next(c for c in cases if c.id == "h-0001")
    scored = score_case(pipeline, canary, judge)
    assert scored["id"] == "h-0001"
    assert scored["scores"]["hit_at_20"] == 1.0
    assert scored["scores"]["mrr"] > 0
    assert 0 <= scored["scores"]["context_precision"] <= 1
    assert scored["scores"]["faithfulness"] in (0.0, 1.0)
    assert scored["passed"] is True, scored
    assert scored["citations"]

    off = next(c for c in cases if c.id == "r-0001")
    scored_off = score_case(pipeline, off, judge)
    assert scored_off["refused"] is True and scored_off["passed"] is True
    assert "recall_at_20" not in scored_off["scores"]
    assert scored_off["scores"]["refusal_correct"] == 1.0


def test_run_eval_produces_contract_shape(corpus_index, corpus_path: Path) -> None:
    pipeline = _pipeline(corpus_index)
    cases = resolve_answer_lines(load_golden(Path("evals/golden/handwritten.jsonl")), corpus_path)
    cases = [c for c in cases if c.id in {"h-0002", "h-0003", "r-0002"}]
    res = run_eval(pipeline, cases, LexicalJudge(), run_name="t", provider="fake", model="fake")
    for key in ("run_id", "commit", "timestamp", "provider", "model", "metrics", "cases"):
        assert key in res
    assert res["n_cases"] == 3
    m = res["metrics"]
    for key in (
        "recall_at_20",
        "precision_at_5",
        "mrr",
        "ndcg_at_10",
        "task_success",
        "p95_latency_ms",
        "cost_per_1k_queries_usd",
        "refusal_recall",
        "false_refusal_rate",
    ):
        assert key in m, key
    assert m["refusal_recall"] == 1.0
    for case in res["cases"]:
        assert {"id", "scores", "passed", "latency_ms", "cost_usd"} <= set(case)


def test_aggregate_handles_empty_and_partial() -> None:
    assert aggregate([])["task_success"] == 0.0
    cases = [
        {
            "scores": {"refused": 0.0, "faithfulness": 1.0},
            "passed": True,
            "latency_ms": 10,
            "cost_usd": 0.001,
            "input_tokens": 10,
            "output_tokens": 5,
            "failure_mode": "retrieval_miss",
        },
        {
            "scores": {"refused": 1.0},
            "passed": True,
            "latency_ms": 20,
            "cost_usd": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "failure_mode": "refusal_miss",
        },
    ]
    m = aggregate(cases)
    assert (
        m["faithfulness"] == 1.0 and m["false_refusal_rate"] == 0.0 and m["refusal_recall"] == 1.0
    )
    assert m["cost_per_1k_queries_usd"] == 0.5
    assert m["p95_latency_ms"] == 20


def test_golden_case_question_property() -> None:
    case = GoldenCase(id="x", input={"question": "q?"}, expected=Expected(refuse=True))
    assert case.question == "q?"
