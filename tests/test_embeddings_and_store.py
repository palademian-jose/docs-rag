from __future__ import annotations

import numpy as np

from docs_rag.embeddings.fake import FakeEmbedder
from docs_rag.vectorstore.memory import MemoryVectorStore


def test_fake_embedder_is_deterministic_and_normalised() -> None:
    emb = FakeEmbedder(dim=64)
    a = emb.embed(["Rockets burn liquid oxygen"])
    b = emb.embed(["Rockets burn liquid oxygen"])
    assert np.allclose(a, b)
    assert a.shape == (1, 64)
    assert abs(float(np.linalg.norm(a[0])) - 1.0) < 1e-5


def test_cosine_prefers_lexically_similar_text() -> None:
    emb = FakeEmbedder(dim=256)
    q = emb.embed(["how long does the canary receive traffic"])[0]
    docs = emb.embed(
        [
            "The canary receives 5% of traffic for ten minutes before promotion.",
            "Cats sleep sixteen hours a day and purr when content.",
        ]
    )
    sims = docs @ q
    assert sims[0] > sims[1]


def test_memory_store_search_save_load(tmp_path) -> None:
    emb = FakeEmbedder(dim=32)
    store = MemoryVectorStore(32)
    texts = ["alpha beta", "gamma delta", "alpha gamma"]
    store.add(["c1", "c2", "c3"], emb.embed(texts))
    assert len(store) == 3
    hits = store.search(emb.embed(["alpha beta"])[0], k=2)
    assert hits[0][0] == "c1"
    assert len(hits) == 2
    assert hits[0][1] >= hits[1][1]

    path = tmp_path / "idx.npz"
    store.save(path)
    loaded = MemoryVectorStore(32)
    loaded.load(path)
    assert len(loaded) == 3
    assert loaded.search(emb.embed(["alpha beta"])[0], k=1)[0][0] == "c1"


def test_memory_store_empty_and_k_bounds() -> None:
    store = MemoryVectorStore(8)
    assert store.search(np.ones(8), k=5) == []
    store.add(["x"], np.ones((1, 8)))
    assert len(store.search(np.ones(8), k=10)) == 1
    store.clear()
    assert len(store) == 0
