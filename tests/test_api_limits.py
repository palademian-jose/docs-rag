from __future__ import annotations

from fastapi.testclient import TestClient

from docs_rag.api.app import client_ip, create_app
from docs_rag.cache import MemoryAnswerCache
from docs_rag.limits import DailyCostCap, RateLimiter
from docs_rag.llm import FakeLLMClient
from docs_rag.pipeline import PipelineConfig, RAGPipeline
from docs_rag.pricing import PriceBook
from docs_rag.rerank.fake import FakeReranker
from docs_rag.retrieval.dense import DenseRetriever

PRICES = PriceBook({"fake-extractive-v1": {"input_per_m": 3.0, "output_per_m": 15.0}})


def _pipeline(corpus_index, cap: DailyCostCap) -> RAGPipeline:
    config = PipelineConfig(top_k=5, candidates=20, refusal_threshold=0.15, cache_enabled=True)
    return RAGPipeline(
        corpus_index,
        FakeLLMClient(),
        DenseRetriever(corpus_index),
        config,
        reranker=FakeReranker(),
        cache=MemoryAnswerCache(),
        pricing=PRICES,
        cost_cap=cap,
    )


def test_rate_limit_returns_429_with_retry_after(settings, corpus_index) -> None:
    now = [0.0]
    limiter = RateLimiter(rate_per_minute=60, burst=2, clock=lambda: now[0])
    app = create_app(settings, _pipeline(corpus_index, DailyCostCap(10)), rate_limiter=limiter)
    client = TestClient(app)
    body = {"question": "How long does the canary receive traffic?"}
    assert client.post("/ask", json=body).status_code == 200
    assert client.post("/ask", json=body).status_code == 200
    r = client.post("/ask", json=body)
    assert r.status_code == 429
    assert r.json()["detail"] == "rate limit exceeded"
    assert int(r.headers["Retry-After"]) >= 1
    # a different client IP has its own bucket
    r2 = client.post("/ask", json=body, headers={"X-Forwarded-For": "10.0.0.9, 1.2.3.4"})
    assert r2.status_code == 200
    now[0] += 60
    assert client.post("/ask", json=body).status_code == 200


def test_cost_cap_returns_429_and_health_reports_spend(settings, corpus_index) -> None:
    cap = DailyCostCap(0.0001)
    app = create_app(settings, _pipeline(corpus_index, cap))
    client = TestClient(app)
    body = {"question": "How long does the canary receive traffic?"}
    first = client.post("/ask", json=body)
    assert first.status_code == 200 and first.json()["cost_usd"] > 0
    cap.record(1.0)
    blocked = client.post("/ask", json={"question": "What is the pull request size limit?"})
    assert blocked.status_code == 429
    assert "cost cap" in blocked.json()["detail"]
    assert blocked.headers["Retry-After"] == "3600"
    # cached answers are still served under the cap
    cached = client.post("/ask", json=body)
    assert cached.status_code == 200 and cached.json()["cache_hit"] is True
    health = client.get("/health").json()
    assert health["daily_cost_cap_usd"] == settings.daily_cost_cap_usd
    assert health["spent_today_usd"] > 1.0
    assert health["cache"] == "memory"


def test_client_ip_prefers_forwarded_header() -> None:
    class Req:
        headers = {"x-forwarded-for": "9.9.9.9, 8.8.8.8"}
        client = type("C", (), {"host": "127.0.0.1"})()

    assert client_ip(Req()) == "9.9.9.9"  # type: ignore[arg-type]
    Req.headers = {}
    assert client_ip(Req()) == "127.0.0.1"  # type: ignore[arg-type]
