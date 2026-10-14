"""Golden set cases (PLAN.md shared contract 3) and chunk-size-independent relevance.

Relevance is defined on source line spans rather than chunk ids so that the same golden set
can score any chunking configuration: a retrieved chunk is relevant when it comes from the
expected document and contains the expected answer line (or overlaps the expected span).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from docs_rag.ingest.chunking import Chunk


class Expected(BaseModel):
    refuse: bool = False
    doc_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    answer_line: int | None = None
    answer_phrase: str | None = None  # resolved to answer_line against the corpus at load time
    chunk_ids: list[str] = Field(default_factory=list)
    answer: str | None = None


class GoldenCase(BaseModel):
    id: str
    input: dict
    expected: Expected
    failure_mode: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str = "synthetic"

    @property
    def question(self) -> str:
        return str(self.input.get("question", ""))


def load_golden(paths: list[Path] | Path) -> list[GoldenCase]:
    paths = [paths] if isinstance(paths, Path) else list(paths)
    cases: list[GoldenCase] = []
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                cases.append(GoldenCase.model_validate_json(line))
    return cases


def save_golden(path: Path, cases: list[GoldenCase]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for case in cases:
            fh.write(json.dumps(case.model_dump(exclude_none=True), ensure_ascii=False) + "\n")


def resolve_answer_lines(cases: list[GoldenCase], corpus_root: Path) -> list[GoldenCase]:
    """Fill ``answer_line`` from ``answer_phrase`` for hand-written cases."""
    for case in cases:
        exp = case.expected
        if exp.answer_line is None and exp.answer_phrase and exp.doc_path:
            doc = corpus_root / exp.doc_path
            if doc.is_file():
                needle = " ".join(exp.answer_phrase.split()).lower()
                lines = doc.read_text(encoding="utf-8").splitlines()
                for n, line in enumerate(lines, start=1):
                    if needle in " ".join(line.split()).lower():
                        exp.answer_line = n
                        break
                if exp.answer_line is None:
                    # phrase may wrap across two lines; search joined pairs
                    for n in range(1, len(lines)):
                        joined = " ".join((lines[n - 1] + " " + lines[n]).split()).lower()
                        if needle in joined:
                            exp.answer_line = n
                            break
    return cases


def is_relevant(chunk: Chunk, expected: Expected) -> bool:
    if expected.refuse or expected.doc_path != chunk.doc_path:
        return False
    if expected.answer_line is not None:
        return chunk.start_line <= expected.answer_line <= chunk.end_line
    if expected.start_line is not None and expected.end_line is not None:
        return chunk.start_line <= expected.end_line and chunk.end_line >= expected.start_line
    return chunk.chunk_id in expected.chunk_ids
