"""Dense (embedding) retriever over the vector store."""

from __future__ import annotations

from docs_rag.ingest.index import Index
from docs_rag.llm.base import approx_tokens
from docs_rag.pricing import PriceBook
from docs_rag.retrieval.types import RetrievedChunk
from docs_rag.tracing import Tracer


class DenseRetriever:
    name = "dense"

    def __init__(
        self, index: Index, *, tracer: Tracer | None = None, pricing: PriceBook | None = None
    ) -> None:
        self.index = index
        self.tracer = tracer or Tracer(None, enabled=False)
        self.pricing = pricing or PriceBook({})

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        if k <= 0 or not self.index.chunks:
            return []
        embedder = self.index.embedder
        with self.tracer.span("embed.query", "other", model=embedder.model_name) as span:
            vector = embedder.embed([query])[0]
            tokens = getattr(embedder, "last_usage_tokens", 0) or approx_tokens(query)
            span.model = embedder.model_name
            span.input_tokens = tokens
            span.cost_usd = self.pricing.token_cost(embedder.model_name, tokens, 0)
            span.meta["provider"] = embedder.provider
        hits = self.index.store.search(vector, k)
        out: list[RetrievedChunk] = []
        for rank, (chunk_id, score) in enumerate(hits, start=1):
            chunk = self.index.by_id.get(chunk_id)
            if chunk is not None:
                out.append(RetrievedChunk(chunk, score, rank, self.name))
        return out
