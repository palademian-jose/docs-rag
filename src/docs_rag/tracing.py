"""Minimal span writer for the PLAN.md JSONL trace schema.

One JSON line per span, appended to TRACE_PATH. A ``Tracer`` holds the current trace id in a
context variable so nested spans share it; ``span()`` is a context manager that fills in
timestamps, latency, status and error kind automatically.
"""

from __future__ import annotations

import contextlib
import json
import threading
import uuid
from collections.abc import Iterator
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SpanKind = str  # llm | retrieval | rerank | tool | cache | verify | other

_current_trace: ContextVar[str | None] = ContextVar("docs_rag_trace_id", default=None)
_current_span: ContextVar[str | None] = ContextVar("docs_rag_span_id", default=None)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass
class Span:
    name: str
    kind: SpanKind
    trace_id: str
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: str | None = None
    start_ts: str = field(default_factory=_now)
    end_ts: str | None = None
    latency_ms: float = 0.0
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cache_hit: bool = False
    feature: str = "rag.answer"
    user_id: str = "anon"
    session_id: str | None = None
    status: str = "ok"
    error_kind: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    _started: float = field(default=0.0, repr=False)

    def to_json(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "latency_ms": round(self.latency_ms, 3),
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 8),
            "cache_hit": self.cache_hit,
            "feature": self.feature,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "status": self.status,
            "error_kind": self.error_kind,
            "meta": self.meta,
        }


class Tracer:
    def __init__(self, path: Path | str | None, *, enabled: bool = True) -> None:
        self.path = Path(path) if path else None
        self.enabled = enabled and self.path is not None
        self._lock = threading.Lock()
        self.spans_written = 0

    @staticmethod
    def current_trace_id() -> str | None:
        return _current_trace.get()

    @contextlib.contextmanager
    def trace(self, trace_id: str | None = None) -> Iterator[str]:
        """Set the active trace id for the duration of the block."""
        tid = trace_id or str(uuid.uuid4())
        token = _current_trace.set(tid)
        try:
            yield tid
        finally:
            _current_trace.reset(token)

    @contextlib.contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind,
        *,
        model: str | None = None,
        feature: str = "rag.answer",
        user_id: str = "anon",
        session_id: str | None = None,
        **meta: Any,
    ) -> Iterator[Span]:
        import time

        trace_id = _current_trace.get() or str(uuid.uuid4())
        span = Span(
            name=name,
            kind=kind,
            trace_id=trace_id,
            parent_span_id=_current_span.get(),
            model=model,
            feature=feature,
            user_id=user_id,
            session_id=session_id,
            meta=dict(meta),
        )
        span._started = time.perf_counter()
        token = _current_span.set(span.span_id)
        try:
            yield span
        except Exception as exc:
            span.status = "error"
            span.error_kind = type(exc).__name__
            raise
        finally:
            _current_span.reset(token)
            span.latency_ms = (time.perf_counter() - span._started) * 1000
            span.end_ts = _now()
            self.write(span)

    def write(self, span: Span) -> None:
        if not self.enabled or self.path is None:
            return
        line = json.dumps(span.to_json(), ensure_ascii=False)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(line + "\n")
            self.spans_written += 1


def read_spans(path: Path | str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
