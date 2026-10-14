"""Tracing is `llmops.tracing` from llm-evalops; this module re-exports it and pins the defaults.

Every span is one JSON line in ``TRACE_PATH`` (``traces/spans.jsonl``) in the shared schema
(PLAN.md contract 2). LLM calls are traced by ``wrap_client`` (see ``RAGPipeline``), the other
stages by ``Tracer.span``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llmops.tracing import (
    JsonlSink,
    MemorySink,
    NullSink,
    Span,
    Tracer,
    get_tracer,
    null_tracer,
    response_cost,
    set_tracer,
    span,
    trace,
    wrap_client,
)

FEATURE = "rag.answer"

__all__ = [
    "FEATURE",
    "JsonlSink",
    "MemorySink",
    "NullSink",
    "Span",
    "Tracer",
    "get_tracer",
    "make_tracer",
    "null_tracer",
    "read_spans",
    "response_cost",
    "set_tracer",
    "span",
    "trace",
    "wrap_client",
]


def make_tracer(path: Path | str | None) -> Tracer:
    """Tracer appending to ``path`` (feature rag.answer); a no-op tracer for an empty path."""
    if not path:
        return null_tracer()
    return Tracer(JsonlSink(path), feature=FEATURE)


def read_spans(path: Path | str) -> list[dict[str, Any]]:
    """Raw span dicts from a JSONL file ([] when it does not exist)."""
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
