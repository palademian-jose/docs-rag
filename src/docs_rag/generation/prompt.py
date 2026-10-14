"""Prompt construction for grounded, cited answers.

The context block format is a small contract shared with the fake LLM backend, which parses it
back out to run its extractive strategy, and with the citation parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from docs_rag.llm.base import Message

REFUSAL_TOKEN = "NOT_IN_DOCS"
CHUNK_OPEN_RE = re.compile(
    r"<<<chunk id=(\S+) source=(\S+) lines=(\d+)-(\d+)>>>\n(.*?)\n<<<end>>>", re.S
)
QUESTION_RE = re.compile(r"^Question:\s*(.+?)\s*$", re.M)

SYSTEM_PROMPT = f"""You are a documentation assistant. Answer the user's question using ONLY the
provided context chunks.

Rules:
1. Every sentence of your answer must end with one or more citations in the form [chunk_id],
   using the ids given in the context. Never invent ids.
2. Quote or closely paraphrase the source; do not add facts that are not in the context.
3. Keep answers short: one to four sentences.
4. If the context does not contain the information needed to answer, reply with exactly
   {REFUSAL_TOKEN} and nothing else."""


@dataclass(frozen=True)
class ContextChunk:
    chunk_id: str
    doc_path: str
    start_line: int
    end_line: int
    text: str


def format_context(chunks: list[ContextChunk]) -> str:
    blocks = [
        f"<<<chunk id={c.chunk_id} source={c.doc_path} lines={c.start_line}-{c.end_line}>>>\n"
        f"{c.text.strip()}\n<<<end>>>"
        for c in chunks
    ]
    return "\n\n".join(blocks)


def build_messages(question: str, chunks: list[ContextChunk]) -> list[Message]:
    user = f"Context:\n{format_context(chunks)}\n\nQuestion: {question.strip()}"
    return [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=user)]


def parse_context(prompt_text: str) -> tuple[str | None, list[ContextChunk]]:
    """Inverse of build_messages: recover the question and the context chunks from a prompt."""
    chunks = [
        ContextChunk(m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), m.group(5))
        for m in CHUNK_OPEN_RE.finditer(prompt_text)
    ]
    qm = QUESTION_RE.search(prompt_text)
    return (qm.group(1) if qm else None), chunks
