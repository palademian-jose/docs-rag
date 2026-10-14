from __future__ import annotations

import httpx

from docs_rag.ingest.chunking import Chunk
from docs_rag.llm import FakeLLMClient
from docs_rag.pipeline import PipelineConfig, RAGPipeline
from docs_rag.rerank import get_reranker
from docs_rag.rerank.cohere import CohereReranker
from docs_rag.rerank.fake import FakeReranker
from docs_rag.retrieval.bm25 import BM25Retriever
from docs_rag.retrieval.dense import DenseRetriever
from docs_rag.retrieval.hybrid import HybridRetriever
from docs_rag.retrieval.types import RetrievedChunk
from docs_rag.settings import Settings


def _rc(cid: str, text: str, rank: int) -> RetrievedChunk:
    chunk = Chunk(cid, "d.md", "D", None, 1, 2, text, 0)
    return RetrievedChunk(chunk, 1.0 / rank, rank, "rrf")


def test_fake_reranker_reorders_by_overlap() -> None:
    candidates = [
        _rc("c1", "Cats sleep sixteen hours a day.", 1),
        _rc("c2", "The canary receives 5% of traffic for ten minutes.", 2),
        _rc("c3", "Canary traffic is mentioned here. Ten minutes is also mentioned.", 3),
    ]
    out = FakeReranker().rerank("how long does the canary receive traffic", candidates, top_k=2)
    assert [r.chunk_id for r in out] == ["c2", "c3"]
    assert out[0].rank == 1 and out[0].source == "rerank"
    assert out[0].score > out[1].score > 0
    assert FakeReranker().score("", "anything") == 0.0


def test_fake_reranker_scores_are_bounded_and_deterministic() -> None:
    r = FakeReranker()
    s1 = r.score("pull request size limit", "Pull requests SHOULD change fewer than 400 lines.")
    s2 = r.score("pull request size limit", "Pull requests SHOULD change fewer than 400 lines.")
    assert s1 == s2 and 0.0 <= s1 <= 1.0


def test_two_stage_pipeline_recall_then_precision(corpus_index) -> None:
    dense = DenseRetriever(corpus_index)
    hybrid = HybridRetriever(dense, BM25Retriever(corpus_index.chunks), candidates_per_retriever=50)
    config = PipelineConfig(top_k=5, candidates=50, refusal_threshold=0.15)
    pipeline = RAGPipeline(corpus_index, FakeLLMClient(), hybrid, config, reranker=FakeReranker())
    result = pipeline.ask("How many replicas do production services run at minimum?")
    assert not result.refused, result
    assert len(result.retrieved_ids) == 50
    assert len(result.context_ids) == 5
    assert any("kubernetes" in c.doc_path for c in result.citations)
    assert result.confidence >= 0.15


def test_reranker_low_score_triggers_refusal(corpus_index) -> None:
    dense = DenseRetriever(corpus_index)
    llm = FakeLLMClient()
    config = PipelineConfig(top_k=5, candidates=50, refusal_threshold=0.15)
    pipeline = RAGPipeline(corpus_index, llm, dense, config, reranker=FakeReranker())
    result = pipeline.ask("Which planet has the most moons?")
    assert result.refused
    assert result.refusal_reason == "low_retrieval_confidence"
    assert llm.calls == []


def test_get_reranker_factory() -> None:
    assert isinstance(get_reranker(Settings(reranker="fake")), FakeReranker)
    assert get_reranker(Settings(reranker="none")) is None
    assert get_reranker(Settings(reranker="fake"), kind="none") is None


def test_cohere_reranker_parses_response(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(self, url, headers=None, json=None):
        captured["url"] = url
        captured["json"] = json
        payload = {
            "results": [
                {"index": 1, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.2},
            ],
            "meta": {"billed_units": {"search_units": 1}},
        }
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    rr = CohereReranker("key")
    out = rr.rerank("q", [_rc("a", "first", 1), _rc("b", "second", 2)], top_k=2)
    assert [r.chunk_id for r in out] == ["b", "a"]
    assert out[0].score == 0.9
    assert captured["json"]["top_n"] == 2 and captured["json"]["model"] == "rerank-v3.5"
    assert rr.last_search_units == 1
