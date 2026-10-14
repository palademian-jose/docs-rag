"""Turn raw model output into a cited answer or a refusal.

Citation integrity rule: a citation is kept only if its chunk id was actually in the context
that the model saw. Ids the model invents are dropped; if an answer ends up with no valid
citation it is treated as unsupported and refused.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from docs_rag.generation.prompt import REFUSAL_TOKEN
from docs_rag.ingest.chunking import Chunk

CITATION_RE = re.compile(r"\[([0-9a-f]{6,40})\]")
_REFUSAL_PHRASES = (
    "not in the docs",
    "does not contain",
    "do not contain",
    "doesn't contain",
    "no information",
    "not mentioned in the",
    "cannot be answered from",
)
REFUSAL_MESSAGE = "I could not find this in the documentation."


class Citation(BaseModel):
    chunk_id: str
    doc_path: str
    start_line: int
    end_line: int
    snippet: str


class ParsedAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    refused: bool = False
    refusal_reason: str | None = None
    invalid_citations: list[str] = Field(default_factory=list)


def looks_like_refusal(text: str) -> bool:
    stripped = text.strip()
    if not stripped or REFUSAL_TOKEN in stripped:
        return True
    lowered = stripped.lower()
    return len(stripped) < 240 and any(p in lowered for p in _REFUSAL_PHRASES)


def make_snippet(chunk: Chunk, max_chars: int = 200) -> str:
    text = " ".join(chunk.text.split())
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


def parse_answer(raw: str, context: list[Chunk]) -> ParsedAnswer:
    by_id = {c.chunk_id: c for c in context}
    if looks_like_refusal(raw):
        return ParsedAnswer(answer=REFUSAL_MESSAGE, refused=True, refusal_reason="model_refused")

    cited_ids = CITATION_RE.findall(raw)
    valid: list[str] = []
    invalid: list[str] = []
    for cid in cited_ids:
        if cid in by_id:
            if cid not in valid:
                valid.append(cid)
        elif cid not in invalid:
            invalid.append(cid)
    # Strip invented ids from the visible text but keep the valid markers.
    cleaned = raw
    for cid in invalid:
        cleaned = cleaned.replace(f"[{cid}]", "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()

    if not valid:
        return ParsedAnswer(
            answer=REFUSAL_MESSAGE,
            refused=True,
            refusal_reason="no_valid_citations",
            invalid_citations=invalid,
        )
    citations = [
        Citation(
            chunk_id=cid,
            doc_path=by_id[cid].doc_path,
            start_line=by_id[cid].start_line,
            end_line=by_id[cid].end_line,
            snippet=make_snippet(by_id[cid]),
        )
        for cid in valid
    ]
    return ParsedAnswer(answer=cleaned, citations=citations, invalid_citations=invalid)
