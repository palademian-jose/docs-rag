"""Dense (embedding) retriever over the vector store."""

from __future__ import annotations

from docs_rag.ingest.index import Index
from docs_rag.retrieval.types import RetrievedChunk


class DenseRetriever:
    name = "dense"

    def __init__(self, index: Index) -> None:
        self.index = index

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        if k <= 0 or not self.index.chunks:
            return []
        vector = self.index.embedder.embed([query])[0]
        hits = self.index.store.search(vector, k)
        out: list[RetrievedChunk] = []
        for rank, (chunk_id, score) in enumerate(hits, start=1):
            chunk = self.index.by_id.get(chunk_id)
            if chunk is not None:
                out.append(RetrievedChunk(chunk, score, rank, self.name))
        return out
