"""Exact-match answer cache: in-memory with TTL, or Redis when REDIS_URL is set.

The key is a hash of the normalised question plus a fingerprint of the pipeline configuration
(retrieval mode, reranker, model, chunking), so a config change never serves stale answers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Any, Protocol, runtime_checkable

log = logging.getLogger(__name__)


def normalise_question(question: str) -> str:
    return " ".join(question.lower().split()).rstrip("?.! ")


def cache_key(question: str, fingerprint: str) -> str:
    raw = f"{fingerprint}\n{normalise_question(question)}"
    return "docs-rag:answer:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


@runtime_checkable
class AnswerCache(Protocol):
    kind: str

    def get(self, key: str) -> dict[str, Any] | None: ...

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None: ...

    def clear(self) -> None: ...


class MemoryAnswerCache:
    kind = "memory"

    def __init__(self, max_entries: int = 10_000) -> None:
        self._data: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()
        self.max_entries = max_entries
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                self.misses += 1
                return None
            expires, value = item
            if expires < time.time():
                del self._data[key]
                self.misses += 1
                return None
            self.hits += 1
            return json.loads(json.dumps(value))  # defensive copy

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        with self._lock:
            if len(self._data) >= self.max_entries:
                oldest = min(self._data.items(), key=lambda kv: kv[1][0])[0]
                del self._data[oldest]
            self._data[key] = (time.time() + ttl_seconds, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


class RedisAnswerCache:
    kind = "redis"

    def __init__(self, url: str) -> None:
        try:
            import redis
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "REDIS_URL set but redis is not installed: uv sync --extra redis"
            ) from exc
        self._client = redis.Redis.from_url(url, decode_responses=True, socket_timeout=2.0)
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            raw = self._client.get(key)
        except Exception as exc:
            log.warning("redis get failed: %s", exc)
            return None
        if raw is None:
            self.misses += 1
            return None
        self.hits += 1
        return json.loads(raw)

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        try:
            self._client.set(key, json.dumps(value), ex=ttl_seconds)
        except Exception as exc:
            log.warning("redis set failed: %s", exc)

    def clear(self) -> None:
        for key in self._client.scan_iter("docs-rag:answer:*"):
            self._client.delete(key)


def get_cache(redis_url: str | None) -> AnswerCache:
    if redis_url:
        return RedisAnswerCache(redis_url)
    return MemoryAnswerCache()
