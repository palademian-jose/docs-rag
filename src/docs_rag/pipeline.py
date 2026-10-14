"""The question-answering pipeline: cache -> retrieve -> rerank -> generate -> cite -> refuse.

Every stage emits a trace span (PLAN.md shared contract 2) through ``llmops.tracing`` and every
paid call is priced from llmops' ``pricing.json``, so an ``AskResult`` carries its own cost and
trace id.
"""

from __future__ import annotations

import time
from typing import Protocol

from llmops.pricing import estimate_cost
from pydantic import BaseModel, Field

from docs_rag.cache import AnswerCache, cache_key
from docs_rag.generation.answer import REFUSAL_MESSAGE, Citation, parse_answer
from docs_rag.generation.prompt import ContextChunk, build_messages
from docs_rag.ingest.index import Index
from docs_rag.limits import DailyCostCap
from docs_rag.llm.base import LLMClient, LLMResponse
from docs_rag.rerank.base import Reranker
from docs_rag.retrieval.types import RetrievedChunk
from docs_rag.settings import Settings
from docs_rag.tracing import FEATURE, Tracer, null_tracer, wrap_client


class CostCapError(RuntimeError):
    """Raised when the daily USD cap has been spent; the API maps it to HTTP 429."""


class Retriever(Protocol):
    name: str

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]: ...


class PipelineConfig(BaseModel):
    top_k: int = 5
    candidates: int = 50
    refusal_threshold: float = 0.15
    max_tokens: int = 512
    model: str | None = None
    cache_enabled: bool = False
    cache_ttl_seconds: int = 3600

    @classmethod
    def from_settings(cls, settings: Settings) -> PipelineConfig:
        return cls(
            top_k=settings.rerank_top_k,
            candidates=settings.candidates_per_retriever,
            refusal_threshold=settings.refusal_threshold,
            model=settings.llm_model,
            cache_enabled=settings.cache_enabled,
            cache_ttl_seconds=settings.cache_ttl_seconds,
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

    def cacheable(self) -> dict:
        return self.model_dump(exclude={"trace_id", "latency_ms", "cache_hit"})


class RAGPipeline:
    def __init__(
        self,
        index: Index,
        llm: LLMClient,
        retriever: Retriever,
        config: PipelineConfig | None = None,
        *,
        reranker: Reranker | None = None,
        tracer: Tracer | None = None,
        cache: AnswerCache | None = None,
        cost_cap: DailyCostCap | None = None,
    ) -> None:
        self.index = index
        self.retriever = retriever
        self.reranker = reranker
        self.config = config or PipelineConfig()
        self.tracer = tracer or null_tracer()
        # Every complete() becomes one costed `generate` llm span (llmops.tracing.wrap_client).
        self.llm = wrap_client(llm, self.tracer, name="generate", feature=FEATURE)
        self.cache = cache
        self.cost_cap = cost_cap

    @property
    def fingerprint(self) -> str:
        """Identifies the configuration; part of the cache key so config changes miss."""
        reranker = self.reranker.name if self.reranker else "none"
        return "|".join(
            [
                self.retriever.name,
                reranker,
                str(self.config.model),
                self.index.embedder.model_name,
                f"{self.index.chunk_size}/{self.index.chunk_overlap}",
                f"top{self.config.top_k}/cand{self.config.candidates}",
                f"thr{self.config.refusal_threshold}",
            ]
        )

    # -- stages -------------------------------------------------------------------------------
    def retrieve(self, question: str) -> list[RetrievedChunk]:
        with self.tracer.span("retrieve", "retrieval", retriever=self.retriever.name) as span:
            candidates = self.retriever.retrieve(question, self.config.candidates)
            span.meta["n_candidates"] = len(candidates)
            span.meta["top_ids"] = [c.chunk_id for c in candidates[:5]]
        return candidates

    def select_context(
        self, question: str, candidates: list[RetrievedChunk]
    ) -> tuple[list[RetrievedChunk], float]:
        """Two-stage retrieval: recall ``candidates`` then rerank down to ``top_k``.

        Returns the context and the cost of the rerank call.
        """
        if self.reranker is None:
            return candidates[: self.config.top_k], 0.0
        with self.tracer.span("rerank", "rerank", model=self.reranker.model_name) as span:
            context = self.reranker.rerank(question, candidates, self.config.top_k)
            span.model = self.reranker.model_name
            span.cost_usd = estimate_cost(self.reranker.model_name, searches=1) or 0.0
            span.meta["n_in"] = len(candidates)
            span.meta["n_out"] = len(context)
            span.meta["top_score"] = context[0].score if context else None
        return context, span.cost_usd

    def generate(self, question: str, context: list[RetrievedChunk]) -> tuple[LLMResponse, float]:
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
        response = self.llm.complete(
            messages, model=self.config.model, max_tokens=self.config.max_tokens
        )
        # Same rule the llm span used: the provider-reported cost wins over tokens x list price.
        cost = response.cost_usd
        if cost is None:
            cost = (
                estimate_cost(
                    response.model, response.usage.input_tokens, response.usage.output_tokens
                )
                or 0.0
            )
        return response, cost

    # -- entry point --------------------------------------------------------------------------
    def ask(
        self, question: str, *, user_id: str = "anon", session_id: str | None = None
    ) -> AskResult:
        start = time.perf_counter()
        with (
            self.tracer.trace(feature=FEATURE, user_id=user_id, session_id=session_id) as trace_id,
            self.tracer.span("rag.ask", "other") as root,
        ):
            key = cache_key(question, self.fingerprint)
            if self.config.cache_enabled and self.cache is not None:
                with self.tracer.span("cache.lookup", "cache") as cs:
                    hit = self.cache.get(key)
                    cs.cache_hit = hit is not None
                if hit is not None:
                    result = AskResult(**hit, trace_id=trace_id, cache_hit=True)
                    result.cost_usd = 0.0
                    result.latency_ms = (time.perf_counter() - start) * 1000
                    root.cache_hit = True
                    root.meta.update(refused=result.refused, cached=True)
                    return result

            if self.cost_cap is not None and not self.cost_cap.allow():
                root.status = "error"
                root.error_kind = "CostCapError"
                raise CostCapError(
                    f"daily cost cap of ${self.cost_cap.cap_usd:.2f} reached "
                    f"(spent ${self.cost_cap.spent_today:.4f})"
                )

            candidates = self.retrieve(question)
            context, rerank_cost = self.select_context(question, candidates)
            confidence = context[0].score if context else 0.0
            result = AskResult(
                answer=REFUSAL_MESSAGE,
                trace_id=trace_id,
                confidence=confidence,
                retrieved_ids=[c.chunk_id for c in candidates],
                context_ids=[c.chunk_id for c in context],
                cost_usd=rerank_cost,
            )
            # The confidence gate only applies to reranker scores, which are calibrated to
            # [0, 1]. Raw retrieval scores (cosine, BM25, RRF) are not comparable across
            # retrievers, so without a reranker the model's own NOT_IN_DOCS refusal is the gate.
            gated = self.reranker is not None and confidence < self.config.refusal_threshold
            if not context or gated:
                result.refused = True
                result.refusal_reason = "low_retrieval_confidence" if context else "no_context"
            else:
                response, gen_cost = self.generate(question, context)
                parsed = parse_answer(response.text, [c.chunk for c in context])
                result.answer = parsed.answer
                result.citations = parsed.citations
                result.refused = parsed.refused
                result.refusal_reason = parsed.refusal_reason
                result.model = response.model
                result.input_tokens = response.usage.input_tokens
                result.output_tokens = response.usage.output_tokens
                result.cost_usd = round(result.cost_usd + gen_cost, 8)

            if self.cost_cap is not None:
                self.cost_cap.record(result.cost_usd)
            if self.config.cache_enabled and self.cache is not None:
                self.cache.set(key, result.cacheable(), self.config.cache_ttl_seconds)
            result.latency_ms = (time.perf_counter() - start) * 1000
            root.cost_usd = result.cost_usd
            root.input_tokens = result.input_tokens
            root.output_tokens = result.output_tokens
            root.model = result.model
            root.meta.update(
                refused=result.refused,
                refusal_reason=result.refusal_reason,
                n_citations=len(result.citations),
                confidence=round(confidence, 4),
            )
            return result
