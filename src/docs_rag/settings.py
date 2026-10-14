"""Single source of configuration, read from the environment and an optional .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["fake", "anthropic", "openai"]
EmbeddingProvider = Literal["fake", "openai", "local"]
VectorStoreKind = Literal["memory", "pgvector"]
RetrievalMode = Literal["dense", "hybrid"]
RerankerKind = Literal["fake", "cohere", "local", "none"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Providers
    llm_provider: LLMProvider = "fake"
    llm_model: str = "claude-sonnet-4-5"
    judge_model: str = "gpt-4o"
    cheap_model: str = "claude-haiku-4-5"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    cohere_api_key: str | None = None

    # Embeddings
    embedding_provider: EmbeddingProvider = "fake"
    embedding_model: str = "text-embedding-3-large"
    embedding_dim: int = 256

    # Vector store
    vector_store: VectorStoreKind = "memory"
    index_path: Path = Path("data/index/index.npz")
    pg_dsn: str = "postgresql://rag:rag@localhost:5432/rag"

    # Retrieval
    corpus_path: Path = Path("data/corpus")
    chunk_size: int = Field(default=512, ge=32)
    chunk_overlap: int = Field(default=64, ge=0)
    retrieval_mode: RetrievalMode = "hybrid"
    candidates_per_retriever: int = 50
    rrf_k: int = 60
    reranker: RerankerKind = "fake"
    rerank_top_k: int = 5
    refusal_threshold: float = 0.15

    # Cache / cost / limits
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    redis_url: str | None = None
    daily_cost_cap_usd: float = 5.0
    rate_limit_per_minute: int = 30
    rate_limit_burst: int = 10

    # Tracing
    trace_path: Path = Path("traces/spans.jsonl")
    pricing_path: Path = Path("pricing.json")

    def has_key(self, provider: str) -> bool:
        return {
            "anthropic": bool(self.anthropic_api_key),
            "openai": bool(self.openai_api_key),
            "cohere": bool(self.cohere_api_key),
        }.get(provider, False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
