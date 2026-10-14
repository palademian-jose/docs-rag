from __future__ import annotations

import pytest

from docs_rag.ingest.chunking import chunk_documents
from docs_rag.retrieval.bm25 import BM25Retriever
from docs_rag.retrieval.dense import DenseRetriever
from docs_rag.retrieval.fusion import rrf
from docs_rag.retrieval.hybrid import HybridRetriever


# -- RRF: known inputs -> known ranks -----------------------------------------------------------
def test_rrf_known_values() -> None:
    fused = rrf([["a", "b", "c"], ["b", "a", "d"]], k=60)
    scores = dict(fused)
    assert scores["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert scores["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert scores["c"] == pytest.approx(1 / 63)
    assert scores["d"] == pytest.approx(1 / 63)
    # a and b tie exactly; ties break by id, then c and d tie and break by id
    assert [doc for doc, _ in fused] == ["a", "b", "c", "d"]


def test_rrf_doc_in_both_lists_beats_single_list_top() -> None:
    # "x" is 2nd in both lists, "y" is 1st in only one: 2/(k+2) > 1/(k+1) for k=60
    fused = rrf([["y", "x"], ["z", "x"]], k=60)
    assert fused[0][0] == "x"
    assert fused[0][1] == pytest.approx(2 / 62)


def test_rrf_larger_k_flattens_rank_differences() -> None:
    small = dict(rrf([["a", "b"]], k=1))
    big = dict(rrf([["a", "b"]], k=1000))
    assert small["a"] / small["b"] == pytest.approx(3 / 2)
    assert big["a"] / big["b"] < 1.01
    with pytest.raises(ValueError):
        rrf([["a"]], k=0)


def test_rrf_ignores_duplicate_ids_within_a_ranking() -> None:
    fused = dict(rrf([["a", "a", "b"]], k=60))
    assert fused["a"] == pytest.approx(1 / 61)
    assert fused["b"] == pytest.approx(1 / 63)


# -- BM25 ---------------------------------------------------------------------------------------
def test_bm25_prefers_exact_terms(small_docs) -> None:
    chunks = chunk_documents(small_docs, size=12, overlap=0)
    bm25 = BM25Retriever(chunks)
    hits = bm25.retrieve("liquid oxygen rockets", k=3)
    assert hits and hits[0].chunk.doc_path == "b.md"
    assert hits[0].rank == 1 and hits[0].source == "bm25"
    assert bm25.retrieve("", k=3) == []
    assert bm25.retrieve("zzzz unknown", k=3) == []


def test_bm25_on_corpus_finds_rare_identifier(corpus_index) -> None:
    bm25 = BM25Retriever(corpus_index.chunks)
    hits = bm25.retrieve("flag-reaper bot", k=5)
    assert any("feature-flags" in h.chunk.doc_path for h in hits[:2])


# -- Hybrid -------------------------------------------------------------------------------------
def test_hybrid_fuses_both_retrievers(corpus_index) -> None:
    dense = DenseRetriever(corpus_index)
    bm25 = BM25Retriever(corpus_index.chunks)
    hybrid = HybridRetriever(dense, bm25, candidates_per_retriever=50, rrf_k=60)
    hits = hybrid.retrieve("How many replicas do production services run?", k=10)
    assert len(hits) == 10
    assert hits[0].source == "rrf" and hits[0].rank == 1
    assert len(hybrid.last_dense) == 50
    assert 0 < len(hybrid.last_bm25) <= 50
    ids = [h.chunk_id for h in hits]
    assert len(ids) == len(set(ids))
    assert any("kubernetes" in h.chunk.doc_path for h in hits[:3])
    # scores are RRF scores, bounded by 2/(k+1)
    assert all(0 < h.score <= 2 / 61 for h in hits)


def test_hybrid_recovers_dense_miss(corpus_index) -> None:
    """A query whose wording matches an identifier should surface via BM25 even if dense is weak."""
    dense = DenseRetriever(corpus_index)
    bm25 = BM25Retriever(corpus_index.chunks)
    hybrid = HybridRetriever(dense, bm25, candidates_per_retriever=50, rrf_k=60)
    query = "lark deploy rollback command"
    fused = hybrid.retrieve(query, k=5)
    assert any("deployments" in h.chunk.doc_path for h in fused)
