from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from docs_rag.settings import get_settings
from docs_rag.tracing import read_spans

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "trace_scenarios.py"


@pytest.fixture(scope="module")
def scenarios(tmp_path_factory: pytest.TempPathFactory):
    get_settings.cache_clear()
    spec = importlib.util.spec_from_file_location("trace_scenarios", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = tmp_path_factory.mktemp("scenarios")
    stats = module.main(["--out", str(out), "--limit", "24"])
    return module, out, stats


def test_each_scenario_writes_its_own_span_directory(scenarios) -> None:
    module, out, stats = scenarios
    assert set(stats) == set(module.SCENARIOS)
    for name in module.SCENARIOS:
        spans = read_spans(out / name / "spans.jsonl")
        assert spans and {s["feature"] for s in spans} == {"rag.answer"}
        assert (
            len({s["trace_id"] for s in spans if s["parent_span_id"] is None})
            == (stats[name]["requests"])
        )


def test_baseline_has_no_cache_and_exact_cache_hits_on_the_second_pass(scenarios) -> None:
    _, out, stats = scenarios
    assert not [s for s in read_spans(out / "baseline" / "spans.jsonl") if s["kind"] == "cache"]
    # every scenario serves the same stream: originals, verbatim repeats, rewordings
    assert {s["requests"] for s in stats.values()} == {72}
    base, exact = stats["baseline"], stats["exact_cache"]
    assert base["exact_hits"] == base["semantic_hits"] == 0
    assert exact["exact_hits"] >= 24 and exact["semantic_hits"] == 0
    assert exact["llm_calls"] < base["llm_calls"] and exact["cost_usd"] < base["cost_usd"]
    assert exact["answers_differing"] == 0, "an exact hit is the answer the pipeline gave"


def test_semantic_scenario_catches_rewordings_the_exact_cache_misses(scenarios) -> None:
    _, out, stats = scenarios
    sem, exact = stats["semantic_cache"], stats["exact_cache"]
    assert sem["semantic_hits"] > 0 and sem["min_semantic_similarity"] >= 0.92
    assert sem["exact_hits"] == exact["exact_hits"]
    assert sem["llm_calls"] < exact["llm_calls"] and sem["cost_usd"] < exact["cost_usd"]
    assert 0 <= sem["answers_differing"] <= sem["semantic_hits"], "audit of semantic false hits"
    spans = read_spans(out / "semantic_cache" / "spans.jsonl")
    assert any(s["name"] == "cache.semantic" and s["cache_hit"] for s in spans)


def test_projected_cost_drops_with_the_cheaper_model(scenarios) -> None:
    _, out, stats = scenarios
    assert stats["baseline"]["cost_usd"] > 0, "fake spans are priced as the model they report"
    assert stats["baseline"]["cost_usd"] > stats["semantic_cache"]["cost_usd"]
    sem, cheap = stats["semantic_cache"], stats["cheaper_model"]
    assert cheap["model"] == "anthropic/claude-haiku-4.5"
    assert cheap["requests"] == sem["requests"] and cheap["llm_calls"] == sem["llm_calls"]
    assert cheap["cost_usd"] < sem["cost_usd"]
    models = {
        s["model"] for s in read_spans(out / "cheaper_model" / "spans.jsonl") if s["kind"] == "llm"
    }
    assert models == {"anthropic/claude-haiku-4.5"}
    rerank = [s for s in read_spans(out / "baseline" / "spans.jsonl") if s["kind"] == "rerank"]
    assert rerank and {s["model"] for s in rerank} == {"rerank-v3.5"}
