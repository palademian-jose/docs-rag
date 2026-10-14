from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ.setdefault("EMBEDDING_PROVIDER", "fake")
os.environ.setdefault("VECTOR_STORE", "memory")
os.environ.setdefault("REDIS_URL", "")

from llmops.pricing import reset_pricing_cache

from docs_rag.embeddings.fake import FakeEmbedder
from docs_rag.ingest.index import Index, build_index
from docs_rag.ingest.loader import Document
from docs_rag.settings import Settings
from docs_rag.vectorstore.memory import MemoryVectorStore

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / "data" / "corpus"


@pytest.fixture(scope="session")
def corpus_path() -> Path:
    return CORPUS


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        llm_provider="fake",
        embedding_provider="fake",
        vector_store="memory",
        corpus_path=CORPUS,
        index_path=tmp_path / "index.npz",
        trace_path=tmp_path / "spans.jsonl",
        redis_url=None,
        cache_enabled=True,
    )


@pytest.fixture(scope="session")
def corpus_index() -> Index:
    """Index over the real sample corpus, built once per test session with the fake embedder."""
    settings = Settings(
        llm_provider="fake",
        embedding_provider="fake",
        vector_store="memory",
        corpus_path=CORPUS,
        redis_url=None,
    )
    return build_index(settings, embedder=FakeEmbedder(256), store=MemoryVectorStore(256))


@pytest.fixture
def small_docs() -> list[Document]:
    return [
        Document(
            doc_path="a.md",
            title="Alpha",
            text="# Alpha\n\n## Cats\n\nCats sleep sixteen hours a day.\nThey purr when content.\n"
            "\n## Dogs\n\nDogs need a daily walk.\nA walk takes thirty minutes.\n",
        ),
        Document(
            doc_path="b.md",
            title="Beta",
            text="# Beta\n\n## Rockets\n\nRockets burn liquid oxygen.\nThe first stage separates "
            "after two minutes.\n",
        ),
    ]


@pytest.fixture
def priced_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point llmops at a price table that gives the fake models a non-zero price.

    The bundled table prices them at zero (they are free); tests that assert on cost need real
    numbers, so they get this one through llmops' PRICING_PATH override.
    """
    path = tmp_path / "pricing.json"
    path.write_text(
        json.dumps(
            {
                "fake-extractive-v1": {"input_per_m": 3.0, "output_per_m": 15.0},
                "fake-lexical-overlap": {"input_per_m": 0, "output_per_m": 0, "per_search": 0.002},
                "fake-hashed-bow-256": {"input_per_m": 0.13, "output_per_m": 0.0},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PRICING_PATH", str(path))
    reset_pricing_cache()
    yield
    reset_pricing_cache()
