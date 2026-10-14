from __future__ import annotations

import json
from pathlib import Path

import llmops.tracing
import pytest

import docs_rag.tracing as tracing
from docs_rag.tracing import FEATURE, NullSink, make_tracer, read_spans

REQUIRED_KEYS = {
    "trace_id", "span_id", "parent_span_id", "name", "kind", "start_ts", "end_ts",
    "latency_ms", "model", "input_tokens", "output_tokens", "cost_usd", "cache_hit",
    "feature", "user_id", "session_id", "status", "error_kind", "meta",
}  # fmt: skip


def test_module_is_llmops_tracing() -> None:
    assert tracing.Tracer is llmops.tracing.Tracer
    assert tracing.wrap_client is llmops.tracing.wrap_client
    assert tracing.JsonlSink is llmops.tracing.JsonlSink


def test_span_schema_and_nesting(tmp_path: Path) -> None:
    tracer = make_tracer(tmp_path / "spans.jsonl")
    with tracer.trace(trace_id="t-1") as tid, tracer.span("answer", "other") as outer:
        assert tid == "t-1"
        with tracer.span("generate", "llm", model="m") as inner:
            inner.input_tokens = 10
            inner.output_tokens = 5
            inner.cost_usd = 0.001
    spans = read_spans(tmp_path / "spans.jsonl")
    assert len(spans) == 2
    inner_json, outer_json = spans  # inner closes first
    assert set(inner_json) == REQUIRED_KEYS
    assert inner_json["trace_id"] == outer_json["trace_id"] == "t-1"
    assert inner_json["parent_span_id"] == outer.span_id
    assert outer_json["parent_span_id"] is None
    assert inner_json["kind"] == "llm" and inner_json["model"] == "m"
    assert inner_json["input_tokens"] == 10 and inner_json["cost_usd"] == 0.001
    assert inner_json["status"] == "ok" and inner_json["error_kind"] is None
    assert inner_json["feature"] == FEATURE == "rag.answer"
    assert inner_json["start_ts"].endswith("Z") and inner_json["end_ts"].endswith("Z")
    assert inner_json["latency_ms"] >= 0


def test_error_spans_record_error_kind(tmp_path: Path) -> None:
    tracer = make_tracer(tmp_path / "spans.jsonl")
    with pytest.raises(ValueError), tracer.span("boom", "tool"):
        raise ValueError("bad")
    span = read_spans(tmp_path / "spans.jsonl")[0]
    assert span["status"] == "error" and span["error_kind"] == "ValueError"


def test_empty_path_gives_a_tracer_that_writes_nothing(tmp_path: Path) -> None:
    tracer = make_tracer(None)
    assert isinstance(tracer.sink, NullSink)
    with tracer.span("x", "other"):
        pass
    assert read_spans(tmp_path / "spans.jsonl") == []


def test_spans_are_valid_json_lines(tmp_path: Path) -> None:
    path = tmp_path / "spans.jsonl"
    tracer = make_tracer(path)
    for i in range(3):
        with tracer.span(f"s{i}", "cache") as s:
            s.cache_hit = i % 2 == 0
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert [json.loads(line)["cache_hit"] for line in lines] == [True, False, True]
