"""The question-answering pipeline: retrieve -> (rerank) -> generate with citations -> refuse."""

from __future__ import annotations

import time
import uuid
from typing import Protocol

from pydantic import BaseModel, Field

from docs_rag.generation.answer import REFUSAL_MESSAGE, Citation, parse_answer
from docs_rag.generation.prompt import ContextChunk, build_messages
from docs_rag.ingest.index import Index
from docs_rag.llm.base import LLMClient
from docs_rag.rerank.base import Reranker
from docs_rag.retrieval.types import RetrievedChunk
from docs_rag.settings import Settings


class Retriever(Protocol):
    name: str

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]: ...


class PipelineConfig(BaseModel):
    top_k: int = 5
    candidates: int = 50
    refusal_threshold: float = 0.15
    max_tokens: int = 512
    model: str | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> PipelineConfig:
        return cls(
            top_k=settings.rerank_top_k,
            candidates=settings.candidates_per_retriever,
            refusal_threshold=settings.refusal_threshold,
            model=settings.llm_model,
        )


class AskResult(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    refused: bool = False
    refusal_reason: str | None = None
    trace_id: str
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    cache_hit: bool = False
    confidence: float = 0.0
    retrieved_ids: list[str] = Field(default_factory=list)  # candidate order, for eval metrics
    context_ids: list[str] = Field(default_factory=list)  # what the model actually saw
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


class RAGPipeline:
    def __init__(
        self,
        index: Index,
        llm: LLMClient,
        retriever: Retriever,
        config: PipelineConfig | None = None,
        *,
        reranker: Reranker | None = None,
    ) -> None:
        self.index = index
        self.llm = llm
        self.retriever = retriever
        self.reranker = reranker
        self.config = config or PipelineConfig()

    # -- stages -------------------------------------------------------------------------------
    def retrieve(self, question: str) -> list[RetrievedChunk]:
        return self.retriever.retrieve(question, self.config.candidates)

    def select_context(
        self, question: str, candidates: list[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        """Two-stage retrieval: recall ``candidates`` then rerank down to ``top_k``."""
        if self.reranker is None:
            return candidates[: self.config.top_k]
        return self.reranker.rerank(question, candidates, self.config.top_k)

    def generate(self, question: str, context: list[RetrievedChunk]):
        ctx = [
            ContextChunk(
                c.chunk.chunk_id,
                c.chunk.doc_path,
                c.chunk.start_line,
                c.chunk.end_line,
                c.chunk.text,
            )
            for c in context
        ]
        messages = build_messages(question, ctx)
        return self.llm.complete(
            messages, model=self.config.model, max_tokens=self.config.max_tokens
        )

    # -- entry point --------------------------------------------------------------------------
    def ask(self, question: str) -> AskResult:
        start = time.perf_counter()
        trace_id = str(uuid.uuid4())
        candidates = self.retrieve(question)
        context = self.select_context(question, candidates)
        confidence = context[0].score if context else 0.0
        result = AskResult(
            answer=REFUSAL_MESSAGE,
            trace_id=trace_id,
            confidence=confidence,
            retrieved_ids=[c.chunk_id for c in candidates],
            context_ids=[c.chunk_id for c in context],
        )
        if not context or confidence < self.config.refusal_threshold:
            result.refused = True
            result.refusal_reason = "low_retrieval_confidence"
        else:
            response = self.generate(question, context)
            parsed = parse_answer(response.text, [c.chunk for c in context])
            result.answer = parsed.answer
            result.citations = parsed.citations
            result.refused = parsed.refused
            result.refusal_reason = parsed.refusal_reason
            result.model = response.model
            result.input_tokens = response.usage.input_tokens
            result.output_tokens = response.usage.output_tokens
        result.latency_ms = (time.perf_counter() - start) * 1000
        return result
