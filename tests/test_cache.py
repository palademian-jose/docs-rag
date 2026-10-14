from __future__ import annotations

import time

from docs_rag.cache import MemoryAnswerCache, cache_key, get_cache, normalise_question


def test_cache_key_normalises_question_and_includes_fingerprint() -> None:
    assert normalise_question("  What IS the  limit? ") == "what is the limit"
    a = cache_key("What is the limit?", "cfg-a")
    b = cache_key("what is the limit", "cfg-a")
    c = cache_key("what is the limit", "cfg-b")
    assert a == b and a != c
    assert a.startswith("docs-rag:answer:")


def test_memory_cache_roundtrip_and_stats() -> None:
    cache = MemoryAnswerCache()
    assert cache.get("k") is None
    cache.set("k", {"answer": "x", "n": 1}, ttl_seconds=60)
    value = cache.get("k")
    assert value == {"answer": "x", "n": 1}
    value["n"] = 2  # copies must not leak back into the cache
    assert cache.get("k")["n"] == 1
    assert cache.hits == 2 and cache.misses == 1
    cache.clear()
    assert len(cache) == 0


def test_memory_cache_expires(monkeypatch) -> None:
    cache = MemoryAnswerCache()
    cache.set("k", {"v": 1}, ttl_seconds=1)
    assert cache.get("k") == {"v": 1}
    real = time.time()
    monkeypatch.setattr(time, "time", lambda: real + 5)
    assert cache.get("k") is None


def test_memory_cache_evicts_oldest() -> None:
    cache = MemoryAnswerCache(max_entries=2)
    cache.set("a", {"v": 1}, ttl_seconds=10)
    cache.set("b", {"v": 2}, ttl_seconds=20)
    cache.set("c", {"v": 3}, ttl_seconds=30)
    assert len(cache) == 2 and cache.get("a") is None
    assert cache.get("c") == {"v": 3}


def test_get_cache_defaults_to_memory() -> None:
    assert get_cache(None).kind == "memory"
    assert get_cache("").kind == "memory"
