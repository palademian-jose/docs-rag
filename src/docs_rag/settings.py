"""Single source of configuration, read from the environment and an optional .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["fake", "openrouter", "anthropic", "openai"]
EmbeddingProvider = Literal["fake", "openai", "local"]
VectorStoreKind = Literal["memory", "pgvector"]
RetrievalMode = Literal["dense", "hybrid"]
RerankerKind = Literal["fake", "cohere", "local", "none"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Providers. ``llm_provider`` left unset means "auto": openrouter > anthropic > openai > fake.
    llm_provider: LLMProvider | None = None
    llm_model: str = "anthropic/claude-sonnet-4.5"
    judge_model: str = "openai/gpt-4.1-mini"
    cheap_model: str = "anthropic/claude-haiku-4.5"
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str | None = None
    openrouter_app_name: str = "docs-rag"
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
    # Sizes are word tokens (roughly 0.75 LLM tokens). Handbook pages are ~350 words, so 128
    # gives about three section-aligned chunks per page.
    chunk_size: int = Field(default=128, ge=32)
    chunk_overlap: int = Field(default=16, ge=0)
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
            "openrouter": bool(self.openrouter_api_key),
            "anthropic": bool(self.anthropic_api_key),
            "openai": bool(self.openai_api_key),
            "cohere": bool(self.cohere_api_key),
        }.get(provider, False)

    def resolved_llm_provider(self) -> LLMProvider:
        """Explicit LLM_PROVIDER wins; otherwise pick the first backend that has a key."""
        if self.llm_provider is not None:
            return self.llm_provider
        for candidate in ("openrouter", "anthropic", "openai"):
            if self.has_key(candidate):
                return candidate  # type: ignore[return-value]
        return "fake"


@lru_cache
def get_settings() -> Settings:
    return Settings()
