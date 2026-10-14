"""Pricing is llmops' pricing.json; these tests pin the contract docs-rag relies on."""

from __future__ import annotations

from pathlib import Path

import pytest
from llmops.pricing import bundled_pricing_path, estimate_cost, load_pricing, normalize_model

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_no_local_copy_of_the_price_table() -> None:
    assert not (REPO_ROOT / "pricing.json").exists(), "pricing.json lives in llm-evalops"
    assert bundled_pricing_path().name == "pricing.json"


def test_bundled_table_has_the_models_docs_rag_uses() -> None:
    table = load_pricing()
    for model in (
        "anthropic/claude-sonnet-4.5",
        "anthropic/claude-haiku-4.5",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "openai/gpt-4.1",
        "openai/gpt-4.1-mini",
        "google/gemini-2.5-flash",
        "text-embedding-3-large",
        "text-embedding-3-small",
        "rerank-v3.5",
        "fake-extractive-v1",
        "fake-hashed-bow-256",
        "fake-lexical-overlap",
    ):
        assert normalize_model(model, table) in table, model


def test_token_cost_math_and_vendor_prefix_fallback() -> None:
    assert estimate_cost("anthropic/claude-sonnet-4.5", 1_000_000, 0) == pytest.approx(3.0)
    assert estimate_cost("claude-sonnet-4-5", 0, 1_000_000) == pytest.approx(15.0)
    assert estimate_cost("claude-sonnet-4-5-20250929", 1000, 500) == pytest.approx(0.0105)
    assert estimate_cost("unknown/model", 1000, 1000) is None


def test_rerank_is_priced_per_search() -> None:
    assert estimate_cost("rerank-v3.5", searches=1) == pytest.approx(0.002)
    assert estimate_cost("cohere/rerank-v3.5", searches=10) == pytest.approx(0.02)
    assert estimate_cost("fake-lexical-overlap", searches=5) == 0.0


def test_fake_models_are_free() -> None:
    assert estimate_cost("fake-extractive-v1", 10_000, 10_000) == 0.0


def test_price_table_override_through_the_environment(priced_models) -> None:
    assert estimate_cost("fake-extractive-v1", 1_000_000, 0) == pytest.approx(3.0)
    assert estimate_cost("fake-lexical-overlap", searches=1) == pytest.approx(0.002)
