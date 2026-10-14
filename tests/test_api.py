from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docs_rag.api.app import create_app
from docs_rag.llm import FakeLLMClient
from docs_rag.pipeline import PipelineConfig, RAGPipeline
from docs_rag.retrieval.dense import DenseRetriever


@pytest.fixture
def client(settings, corpus_index) -> TestClient:
    config = PipelineConfig(top_k=5, candidates=50, refusal_threshold=0.0)
    pipeline = RAGPipeline(corpus_index, FakeLLMClient(), DenseRetriever(corpus_index), config)
    app = create_app(settings, pipeline)
    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["provider"] == "fake"
    assert body["chunks"] > 100


def test_ask_returns_cited_answer(client: TestClient) -> None:
    r = client.post("/ask", json={"question": "How long does the canary receive 5% of traffic?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["refused"] is False
    assert body["citations"], body
    cite = body["citations"][0]
    assert set(cite) == {"chunk_id", "doc_path", "start_line", "end_line", "snippet"}
    assert body["trace_id"] and body["latency_ms"] >= 0 and "cost_usd" in body
    # the cited document is served with line anchors
    doc = client.get(f"/docs/{cite['doc_path']}", params={"start": cite["start_line"]})
    assert doc.status_code == 200
    assert f'id="L{cite["start_line"]}"' in doc.text
    assert 'class="line hl"' in doc.text


def test_ask_refuses_off_corpus(client: TestClient) -> None:
    r = client.post("/ask", json={"question": "Who won the 1998 football world cup?"})
    assert r.status_code == 200
    body = r.json()
    assert body["refused"] is True
    assert body["citations"] == []


def test_ask_validates_input(client: TestClient) -> None:
    assert client.post("/ask", json={"question": ""}).status_code == 422
    assert client.post("/ask", json={}).status_code == 422


def test_docs_rejects_traversal_and_missing(client: TestClient) -> None:
    assert client.get("/docs/../pyproject.toml").status_code in (404, 400)
    assert client.get("/docs/does-not-exist.md").status_code == 404


def test_ui_is_served(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "<title>docs-rag</title>" in r.text
