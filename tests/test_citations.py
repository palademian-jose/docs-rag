from __future__ import annotations

from docs_rag.generation.answer import REFUSAL_MESSAGE, looks_like_refusal, parse_answer
from docs_rag.ingest.chunking import Chunk


def _chunk(cid: str, path: str = "x.md", start: int = 1, end: int = 3) -> Chunk:
    return Chunk(cid, path, "X", "H", start, end, "Some text here.\nMore text.\nEnd.", 0)


CTX = [_chunk("aaaaaaaaaa"), _chunk("bbbbbbbbbb", "y.md", 10, 12)]


def test_citations_map_to_real_chunks() -> None:
    parsed = parse_answer("Fact one. [aaaaaaaaaa] Fact two. [bbbbbbbbbb]", CTX)
    assert not parsed.refused
    assert [c.chunk_id for c in parsed.citations] == ["aaaaaaaaaa", "bbbbbbbbbb"]
    assert parsed.citations[1].doc_path == "y.md"
    assert (parsed.citations[1].start_line, parsed.citations[1].end_line) == (10, 12)
    assert parsed.citations[0].snippet.startswith("Some text here.")


def test_invented_citations_are_dropped() -> None:
    parsed = parse_answer("Fact. [aaaaaaaaaa] Made up. [ffffffffff]", CTX)
    assert [c.chunk_id for c in parsed.citations] == ["aaaaaaaaaa"]
    assert parsed.invalid_citations == ["ffffffffff"]
    assert "[ffffffffff]" not in parsed.answer


def test_answer_without_valid_citations_is_refused() -> None:
    parsed = parse_answer("Confident claim with no support. [ffffffffff]", CTX)
    assert parsed.refused
    assert parsed.refusal_reason == "no_valid_citations"
    assert parsed.answer == REFUSAL_MESSAGE
    assert parsed.citations == []


def test_model_refusal_token_and_phrases() -> None:
    assert parse_answer("NOT_IN_DOCS", CTX).refused
    assert parse_answer("The provided context does not contain that information.", CTX).refused
    assert parse_answer("", CTX).refused
    assert not looks_like_refusal("The canary runs for ten minutes. [aaaaaaaaaa]")


def test_duplicate_citations_collapse() -> None:
    parsed = parse_answer("A. [aaaaaaaaaa] B. [aaaaaaaaaa]", CTX)
    assert len(parsed.citations) == 1
