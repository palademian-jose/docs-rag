"""Wire settings into a ready-to-use pipeline."""

from __future__ import annotations

from docs_rag.ingest.index import Index, load_or_build_index
from docs_rag.llm import get_client
from docs_rag.llm.base import LLMClient
from docs_rag.pipeline import PipelineConfig, RAGPipeline
from docs_rag.retrieval.dense import DenseRetriever
from docs_rag.settings import Settings, get_settings


def build_pipeline(
    settings: Settings | None = None,
    *,
    index: Index | None = None,
    llm: LLMClient | None = None,
    config: PipelineConfig | None = None,
) -> RAGPipeline:
    settings = settings or get_settings()
    index = index or load_or_build_index(settings)
    llm = llm or get_client(settings)
    config = config or PipelineConfig.from_settings(settings)
    retriever = DenseRetriever(index)
    return RAGPipeline(index, llm, retriever, config)
