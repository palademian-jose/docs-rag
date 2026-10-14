"""Cohere Rerank backend over the v2 REST API (no SDK dependency)."""

from __future__ import annotations

import httpx

from docs_rag.rerank.base import take_top
from docs_rag.retrieval.types import RetrievedChunk

COHERE_RERANK_URL = "https://api.cohere.com/v2/rerank"


class CohereReranker:
    name = "cohere"

    def __init__(self, api_key: str, *, model: str = "rerank-v3.5", timeout: float = 30.0) -> None:
        self.model_name = model
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._client = httpx.Client(timeout=timeout)
        self.last_search_units = 0

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []
        payload = {
            "model": self.model_name,
            "query": query,
            "documents": [c.chunk.embed_text for c in candidates],
            "top_n": min(top_k, len(candidates)),
        }
        resp = self._client.post(COHERE_RERANK_URL, headers=self._headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        self.last_search_units = int(
            data.get("meta", {}).get("billed_units", {}).get("search_units", 1)
        )
        scored = [
            (candidates[item["index"]], float(item["relevance_score"]))
            for item in data.get("results", [])
        ]
        return take_top(scored, top_k)
