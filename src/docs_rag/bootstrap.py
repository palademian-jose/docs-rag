"""Wire settings into a ready-to-use pipeline (index, LLM, retriever, reranker, tracing, cache)."""

from __future__ import annotations

from docs_rag.cache import AnswerCache, SemanticAnswerCache, get_cache
from docs_rag.ingest.index import Index, load_or_build_index
from docs_rag.limits import DailyCostCap
from docs_rag.llm import get_client
from docs_rag.llm.base import LLMClient
from docs_rag.pipeline import PipelineConfig, RAGPipeline
from docs_rag.rerank import get_reranker
from docs_rag.retrieval import build_retriever
from docs_rag.settings import Settings, get_settings
from docs_rag.tracing import Tracer, make_tracer


def build_pipeline(
    settings: Settings | None = None,
    *,
    index: Index | None = None,
    llm: LLMClient | None = None,
    config: PipelineConfig | None = None,
    retrieval_mode: str | None = None,
    reranker: str | None = None,
    cache_enabled: bool | None = None,
    semantic_cache: SemanticAnswerCache | bool | None = None,
    tracer: Tracer | None = None,
    cache: AnswerCache | None = None,
    cost_cap: DailyCostCap | None = None,
) -> RAGPipeline:
    """Build a pipeline.

    ``retrieval_mode`` ("dense"/"hybrid"), ``reranker`` ("fake"/"cohere"/"local"/"none") and
    ``cache_enabled`` override the settings so the eval script can build each variant.
    ``semantic_cache`` is a ready ``SemanticAnswerCache``, ``True``/``False`` to force it on or off,
    or ``None`` to follow ``SEMANTIC_CACHE_ENABLED``.
    """
    settings = settings or get_settings()
    index = index or load_or_build_index(settings)
    llm = llm or get_client(settings)
    config = config or PipelineConfig.from_settings(settings)
    if cache_enabled is not None:
        config = config.model_copy(update={"cache_enabled": cache_enabled})
    tracer = tracer or make_tracer(settings.trace_path)
    if cache is None and config.cache_enabled:
        cache = get_cache(settings.redis_url)
    if semantic_cache is None:
        semantic_cache = settings.semantic_cache_enabled
    if semantic_cache is True:
        semantic_cache = SemanticAnswerCache(settings.semantic_cache_threshold, tracer=tracer)
    if cost_cap is None:
        cost_cap = DailyCostCap(settings.daily_cost_cap_usd)
    retriever = build_retriever(index, settings, mode=retrieval_mode, tracer=tracer)
    return RAGPipeline(
        index,
        llm,
        retriever,
        config,
        reranker=get_reranker(settings, kind=reranker),
        tracer=tracer,
        cache=cache,
        semantic_cache=semantic_cache if isinstance(semantic_cache, SemanticAnswerCache) else None,
        cost_cap=cost_cap,
    )
