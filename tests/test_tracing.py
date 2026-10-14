from __future__ import annotations

import json
from pathlib import Path

import pytest

from docs_rag.tracing import Tracer, read_spans

REQUIRED_KEYS = {
    "trace_id", "span_id", "parent_span_id", "name", "kind", "start_ts", "end_ts",
    "latency_ms", "model", "input_tokens", "output_tokens", "cost_usd", "cache_hit",
    "feature", "user_id", "session_id", "status", "error_kind", "meta",
}  # fmt: skip


def test_span_schema_and_nesting(tmp_path: Path) -> None:
    tracer = Tracer(tmp_path / "spans.jsonl")
    with tracer.trace("t-1") as tid, tracer.span("answer", "other") as outer:
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
    assert inner_json["start_ts"].endswith("Z") and inner_json["end_ts"].endswith("Z")
    assert inner_json["latency_ms"] >= 0
    assert tracer.spans_written == 2


def test_error_spans_record_error_kind(tmp_path: Path) -> None:
    tracer = Tracer(tmp_path / "spans.jsonl")
    with pytest.raises(ValueError), tracer.span("boom", "tool"):
        raise ValueError("bad")
    span = read_spans(tmp_path / "spans.jsonl")[0]
    assert span["status"] == "error" and span["error_kind"] == "ValueError"


def test_disabled_tracer_writes_nothing(tmp_path: Path) -> None:
    tracer = Tracer(tmp_path / "spans.jsonl", enabled=False)
    with tracer.span("x", "other"):
        pass
    assert not (tmp_path / "spans.jsonl").exists()
    assert Tracer(None).enabled is False


def test_spans_are_valid_json_lines(tmp_path: Path) -> None:
    path = tmp_path / "spans.jsonl"
    tracer = Tracer(path)
    for i in range(3):
        with tracer.span(f"s{i}", "cache") as s:
            s.cache_hit = i % 2 == 0
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert [json.loads(line)["cache_hit"] for line in lines] == [True, False, True]
