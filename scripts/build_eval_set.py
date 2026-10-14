"""Generate a synthetic golden set: one question per chunk, plus a human-verification sample.

Fake provider: template questions from the chunk heading and its first substantive sentence.
Real provider: the CHEAP_MODEL writes a natural question answerable only from the chunk.

Outputs
  evals/golden/questions.jsonl   PLAN.md golden format, source="synthetic"
  evals/human_labels.jsonl       ~20% sample with the pipeline's answer, for hand labelling
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

from docs_rag.bootstrap import build_pipeline
from docs_rag.evals.golden import Expected, GoldenCase, load_golden, save_golden
from docs_rag.ingest.chunking import Chunk
from docs_rag.ingest.index import load_or_build_index
from docs_rag.llm import Message, get_client
from docs_rag.settings import get_settings
from docs_rag.textutil import content_tokens, split_sentences

log = logging.getLogger("build_eval_set")


def key_sentence(chunk: Chunk) -> str | None:
    for sentence in split_sentences(chunk.text):
        if sentence.lower().startswith("owner:"):
            continue
        if len(content_tokens(sentence)) >= 6:
            return sentence
    return None


def locate_line(chunk: Chunk, sentence: str) -> int:
    needle = " ".join(sentence.split())[:30].lower()
    for offset, line in enumerate(chunk.text.splitlines()):
        if needle and needle in " ".join(line.split()).lower():
            return chunk.start_line + offset
    return chunk.start_line


def template_question(chunk: Chunk, sentence: str) -> str:
    lead = " ".join(re.sub(r"[`*]", "", sentence).split()[:6]).rstrip(",.;:")
    if not chunk.heading or chunk.heading == chunk.doc_title:
        return f"What does the {chunk.doc_title} page say regarding '{lead}'?"
    topic = chunk.heading.lower()
    return f"What does the {chunk.doc_title} page say about {topic} regarding '{lead}'?"


def llm_question(client, chunk: Chunk, sentence: str, model: str) -> tuple[str, str] | None:
    prompt = (
        "Write ONE short, natural question that an engineer might ask which is answered by the "
        "following passage, and the one-sentence answer taken from the passage. The question "
        "must not be answerable from general knowledge.\n\n"
        f"Document: {chunk.doc_title}\nSection: {chunk.heading or '-'}\n\n"
        f"Passage:\n{chunk.text}\n\n"
        f"Key sentence: {sentence}\n\n"
        'Reply with JSON only: {"question": "...", "answer": "..."}'
    )
    resp = client.complete([Message(role="user", content=prompt)], model=model, max_tokens=300)
    match = re.search(r"\{.*\}", resp.text, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return str(data["question"]).strip(), str(data.get("answer") or sentence).strip()
    except (json.JSONDecodeError, KeyError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("evals/golden/questions.jsonl"))
    parser.add_argument("--labels", type=Path, default=Path("evals/human_labels.jsonl"))
    parser.add_argument("--sample-every", type=int, default=5, help="1 in N cases to hand-label")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-keep-labels", action="store_true", help="discard existing labels")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    settings = get_settings()
    provider = settings.resolved_llm_provider()
    index = load_or_build_index(settings)
    client = get_client(settings, role="cheap") if provider != "fake" else None

    cases: list[GoldenCase] = []
    seen: set[str] = set()
    for chunk in index.chunks:
        sentence = key_sentence(chunk)
        if sentence is None:
            continue
        norm = " ".join(sentence.lower().split())
        if norm in seen:
            continue
        seen.add(norm)
        question, answer = template_question(chunk, sentence), sentence
        if client is not None:
            generated = llm_question(client, chunk, sentence, settings.cheap_model)
            if generated:
                question, answer = generated
        cases.append(
            GoldenCase(
                id=f"g-{len(cases) + 1:04d}",
                input={"question": question},
                expected=Expected(
                    doc_path=chunk.doc_path,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    answer_line=locate_line(chunk, sentence),
                    chunk_ids=[chunk.chunk_id],
                    answer=answer,
                ),
                failure_mode="retrieval_miss",
                tags=[Path(chunk.doc_path).stem, "synthetic", "llm" if client else "template"],
                source="synthetic",
            )
        )
        if args.limit and len(cases) >= args.limit:
            break
    save_golden(args.out, cases)
    log.info("wrote %d synthetic cases to %s (provider=%s)", len(cases), args.out, provider)

    # Human verification sample: every Nth synthetic case plus every hand-written in-corpus case.
    existing: dict[str, dict] = {}
    if args.labels.exists() and not args.no_keep_labels:
        for line in args.labels.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                existing[row["id"]] = row
    handwritten = Path("evals/golden/handwritten.jsonl")
    extra = (
        [c for c in load_golden(handwritten) if not c.expected.refuse]
        if handwritten.exists()
        else []
    )
    sample = cases[:: args.sample_every] + extra

    pipeline = build_pipeline(settings, index=index)
    rows: list[dict] = []
    for case in sample:
        result = pipeline.ask(case.question)
        context = [pipeline.index.by_id[c.chunk_id].text for c in result.citations]
        prev = existing.get(case.id)
        keep = prev is not None and prev.get("answer") == result.answer
        rows.append(
            {
                "id": case.id,
                "criterion": "faithfulness",
                "question": case.question,
                "expected_answer": case.expected.answer,
                "answer": result.answer,
                "refused": result.refused,
                "context": context,
                "human_pass": prev.get("human_pass") if keep else None,
                "verified": bool(prev.get("verified")) if keep else False,
                "notes": prev.get("notes", "") if keep else "",
            }
        )
    args.labels.parent.mkdir(parents=True, exist_ok=True)
    with args.labels.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    labelled = sum(1 for r in rows if r["human_pass"] is not None)
    log.info(
        "wrote %d rows for hand verification to %s (%d labelled)", len(rows), args.labels, labelled
    )


if __name__ == "__main__":
    main()
