from __future__ import annotations

from docs_rag.llm import FakeLLMClient
from docs_rag.pipeline import PipelineConfig, RAGPipeline
from docs_rag.retrieval.dense import DenseRetriever


def _dense_pipeline(corpus_index, **cfg) -> RAGPipeline:
    config = PipelineConfig(top_k=5, candidates=50, refusal_threshold=0.0, **cfg)
    return RAGPipeline(corpus_index, FakeLLMClient(), DenseRetriever(corpus_index), config)


def test_dense_pipeline_answers_with_citations(corpus_index) -> None:
    pipeline = _dense_pipeline(corpus_index)
    result = pipeline.ask("How long does the canary receive 5% of traffic before promotion?")
    assert not result.refused, result
    assert result.citations, "answer must carry citations"
    assert all(c.chunk_id in corpus_index.by_id for c in result.citations)
    assert any("deployments" in c.doc_path for c in result.citations)
    assert len(result.retrieved_ids) == min(50, len(corpus_index.chunks))
    assert len(result.context_ids) == 5
    assert result.latency_ms >= 0


def test_dense_pipeline_refuses_off_corpus(corpus_index) -> None:
    pipeline = _dense_pipeline(corpus_index)
    result = pipeline.ask("What is the boiling point of mercury on Venus?")
    assert result.refused
    assert result.citations == []


def test_low_confidence_refuses_before_generation(corpus_index) -> None:
    llm = FakeLLMClient()
    config = PipelineConfig(top_k=5, candidates=10, refusal_threshold=10.0)
    pipeline = RAGPipeline(corpus_index, llm, DenseRetriever(corpus_index), config)
    result = pipeline.ask("What is the pull request size limit?")
    assert result.refused and result.refusal_reason == "low_retrieval_confidence"
    assert llm.calls == [], "LLM must not be called when confidence is too low"
