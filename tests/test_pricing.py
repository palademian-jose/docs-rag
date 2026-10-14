from __future__ import annotations

import pytest

from docs_rag.pricing import PriceBook, load_pricing


def test_pricing_file_has_required_models() -> None:
    book = load_pricing("pricing.json")
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
    ):
        assert book.lookup(model) is not None, model


def test_token_cost_math() -> None:
    book = PriceBook({"m": {"input_per_m": 3.0, "output_per_m": 15.0}})
    assert book.token_cost("m", 1_000_000, 0) == pytest.approx(3.0)
    assert book.token_cost("m", 0, 1_000_000) == pytest.approx(15.0)
    assert book.token_cost("m", 1000, 500) == pytest.approx(0.003 + 0.0075)
    assert book.token_cost("m", 0, 0) == 0.0


def test_lookup_fallbacks() -> None:
    book = PriceBook({"claude-sonnet-4-5": {"input_per_m": 3.0, "output_per_m": 15.0}})
    assert book.lookup("anthropic/claude-sonnet-4.5") is not None  # strip vendor + dots
    assert book.lookup("claude-sonnet-4-5-20250929") is not None  # dated snapshot
    assert book.lookup("unknown/model") is None
    assert "unknown/model" in book.unknown
    assert book.token_cost("unknown/model", 1000, 1000) == 0.0
    assert book.lookup(None) is None


def test_per_call_pricing() -> None:
    book = load_pricing("pricing.json")
    assert book.call_cost("rerank-v3.5", 1) == pytest.approx(0.002)
    assert book.call_cost("cohere/rerank-v3.5", 10) == pytest.approx(0.02)
    assert book.call_cost("fake-lexical-overlap", 5) == 0.0


def test_fake_models_are_free() -> None:
    book = load_pricing("pricing.json")
    assert book.token_cost("fake-extractive-v1", 10_000, 10_000) == 0.0
