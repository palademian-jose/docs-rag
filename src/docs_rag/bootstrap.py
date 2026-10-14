"""Wire settings into a ready-to-use pipeline."""

from __future__ import annotations

from docs_rag.ingest.index import Index, load_or_build_index
from docs_rag.llm import get_client
from docs_rag.llm.base import LLMClient
from docs_rag.pipeline import PipelineConfig, RAGPipeline
from docs_rag.rerank import get_reranker
from docs_rag.retrieval import build_retriever
from docs_rag.settings import Settings, get_settings


def build_pipeline(
    settings: Settings | None = None,
    *,
    index: Index | None = None,
    llm: LLMClient | None = None,
    config: PipelineConfig | None = None,
    retrieval_mode: str | None = None,
    reranker: str | None = None,
    cache_enabled: bool | None = None,
) -> RAGPipeline:
    """Build a pipeline.

    ``retrieval_mode`` ("dense"/"hybrid"), ``reranker`` ("fake"/"cohere"/"local"/"none") and
    ``cache_enabled`` override the settings so the eval script can build each variant.
    """
    settings = settings or get_settings()
    index = index or load_or_build_index(settings)
    llm = llm or get_client(settings)
    config = config or PipelineConfig.from_settings(settings)
    if cache_enabled is not None:
        config = config.model_copy(update={"cache_enabled": cache_enabled})
    retriever = build_retriever(index, settings, mode=retrieval_mode)
    return RAGPipeline(
        index, llm, retriever, config, reranker=get_reranker(settings, kind=reranker)
    )
