"""Ask a few questions against the corpus from the command line (works with LLM_PROVIDER=fake)."""

from __future__ import annotations

import argparse
import json
import logging

from docs_rag.bootstrap import build_pipeline
from docs_rag.settings import get_settings

DEFAULT_QUESTIONS = [
    "How long does the canary receive traffic before it is promoted?",
    "What is the pull request size limit?",
    "Which Python version do services target, and what manages dependencies?",
    "Who approves break-glass access requests?",
    "What is the capital of France?",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("questions", nargs="*", help="questions to ask (defaults to a demo set)")
    parser.add_argument("--json", action="store_true", help="print raw JSON results")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    settings = get_settings()
    pipeline = build_pipeline(settings)
    print(f"provider={settings.resolved_llm_provider()} chunks={len(pipeline.index.chunks)}\n")
    for question in args.questions or DEFAULT_QUESTIONS:
        result = pipeline.ask(question)
        if args.json:
            print(json.dumps(result.model_dump(), indent=2))
            continue
        print(f"Q: {question}")
        status = "REFUSED" if result.refused else "ANSWER"
        print(f"{status} ({result.latency_ms:.0f} ms, confidence={result.confidence:.2f})")
        print(f"  {result.answer}")
        for c in result.citations:
            print(f"  - [{c.chunk_id}] {c.doc_path}#L{c.start_line}-L{c.end_line}")
        print()


if __name__ == "__main__":
    main()
