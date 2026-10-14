from __future__ import annotations

from itertools import pairwise

import pytest

from docs_rag.ingest.chunking import chunk_document, chunk_documents, count_tokens, make_chunk_id
from docs_rag.ingest.loader import Document, load_corpus


def _doc(n_lines: int, words_per_line: int = 10) -> Document:
    lines = [" ".join(f"w{i}x{j}" for j in range(words_per_line)) for i in range(n_lines)]
    return Document(doc_path="d.md", title="D", text="\n".join(lines))


def test_chunks_respect_size_and_cover_every_line() -> None:
    doc = _doc(50)
    chunks = chunk_document(doc, size=40, overlap=0)
    assert chunks, "expected chunks"
    for c in chunks:
        assert count_tokens(c.text) <= 40
    covered = set()
    for c in chunks:
        covered.update(range(c.start_line, c.end_line + 1))
    assert covered == set(range(1, 51))
    # without overlap chunks are contiguous and non-overlapping
    for a, b in pairwise(chunks):
        assert b.start_line == a.end_line + 1


def test_overlap_repeats_lines() -> None:
    doc = _doc(30)
    chunks = chunk_document(doc, size=50, overlap=10)
    assert len(chunks) > 1
    for a, b in pairwise(chunks):
        assert b.start_line <= a.end_line, "overlapping chunks must share lines"
        assert b.start_line > a.start_line, "cursor must always advance"


def test_single_long_line_still_chunks() -> None:
    doc = Document(doc_path="l.md", title="L", text=" ".join(f"t{i}" for i in range(500)))
    chunks = chunk_document(doc, size=64, overlap=8)
    assert len(chunks) == 1
    assert chunks[0].start_line == chunks[0].end_line == 1


def test_chunk_ids_are_stable_and_unique(small_docs) -> None:
    chunks = chunk_documents(small_docs, size=12, overlap=0)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert ids[0] == make_chunk_id("a.md", chunks[0].start_line, chunks[0].end_line)
    again = chunk_documents(small_docs, size=12, overlap=0)
    assert [c.chunk_id for c in again] == ids


def test_heading_and_title_are_tracked(small_docs) -> None:
    chunks = chunk_document(small_docs[0], size=12, overlap=0)
    headings = {c.heading for c in chunks}
    assert "Cats" in headings or "Dogs" in headings
    assert all(c.doc_title == "Alpha" for c in chunks)
    assert chunks[0].embed_text.startswith("Alpha")


def test_invalid_parameters() -> None:
    doc = _doc(5)
    with pytest.raises(ValueError):
        chunk_document(doc, size=0, overlap=0)
    with pytest.raises(ValueError):
        chunk_document(doc, size=10, overlap=10)


def test_load_corpus_reads_markdown(corpus_path) -> None:
    docs = load_corpus(corpus_path)
    assert len(docs) >= 40
    assert all(d.doc_path.endswith(".md") for d in docs)
    assert any("Handbook" in d.title for d in docs)
