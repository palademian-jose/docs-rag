"""Judge interface (PLAN.md shared contract 4).

``judge(criterion, input, output, reference) -> {"pass": bool, "reason": str}``

Criteria:
- ``faithfulness``: every claim in ``output["answer"]`` is supported by ``output["context"]``.
- ``answer_relevance``: the answer addresses ``input["question"]`` (and matches
  ``reference["answer"]`` when given).
- ``context_relevance``: ``output["context"]`` (one chunk) is useful for the question.

Two implementations: ``LexicalJudge`` (deterministic token-overlap heuristics, used with the
fake provider and in CI) and ``LLMJudge`` (criterion-specific rubric, JSON verdict).
"""

from __future__ import annotations

import json
import re
from typing import Any, Protocol, runtime_checkable

from docs_rag.generation.answer import CITATION_RE
from docs_rag.llm.base import LLMClient, Message
from docs_rag.textutil import content_tokens, overlap_ratio, split_sentences

CRITERIA = ("faithfulness", "answer_relevance", "context_relevance")


@runtime_checkable
class Judge(Protocol):
    name: str

    def judge(
        self, criterion: str, input: dict, output: dict, reference: dict | None = None
    ) -> dict: ...


def _strip_citations(text: str) -> str:
    return CITATION_RE.sub("", text).strip()


def _context_texts(output: dict) -> list[str]:
    ctx = output.get("context") or []
    if isinstance(ctx, str):
        return [ctx]
    return [c if isinstance(c, str) else str(c.get("text", "")) for c in ctx]


class LexicalJudge:
    name = "lexical"

    def __init__(
        self,
        *,
        support_threshold: float = 0.6,
        relevance_threshold: float = 0.3,
        reference_threshold: float = 0.4,
    ) -> None:
        self.support_threshold = support_threshold
        self.relevance_threshold = relevance_threshold
        self.reference_threshold = reference_threshold

    def judge(
        self, criterion: str, input: dict, output: dict, reference: dict | None = None
    ) -> dict:
        if criterion == "faithfulness":
            return self._faithfulness(output)
        if criterion == "answer_relevance":
            return self._answer_relevance(input, output, reference)
        if criterion == "context_relevance":
            return self._context_relevance(input, output)
        raise ValueError(f"unknown criterion: {criterion}")

    def _faithfulness(self, output: dict) -> dict:
        answer = _strip_citations(str(output.get("answer", "")))
        contexts = [content_tokens(t) for t in _context_texts(output)]
        sentences = split_sentences(answer) or ([answer] if answer else [])
        if not sentences:
            return {"pass": False, "reason": "empty answer"}
        if not contexts:
            return {"pass": False, "reason": "no context to support the answer"}
        weakest = 1.0
        weakest_sentence = ""
        for sentence in sentences:
            toks = content_tokens(sentence)
            if len(toks) < 2:
                continue
            support = max(overlap_ratio(toks, ctx) for ctx in contexts)
            if support < weakest:
                weakest, weakest_sentence = support, sentence
        passed = weakest >= self.support_threshold
        reason = (
            f"all sentences supported (min support {weakest:.2f})"
            if passed
            else f"unsupported sentence (support {weakest:.2f}): {weakest_sentence[:120]!r}"
        )
        return {"pass": passed, "reason": reason, "score": round(weakest, 3)}

    def _answer_relevance(self, input: dict, output: dict, reference: dict | None) -> dict:
        answer = content_tokens(_strip_citations(str(output.get("answer", ""))))
        if not answer:
            return {"pass": False, "reason": "empty answer"}
        if reference and reference.get("answer"):
            ref = content_tokens(str(reference["answer"]))
            score = overlap_ratio(ref, answer)
            passed = score >= self.reference_threshold
            return {
                "pass": passed,
                "reason": f"reference overlap {score:.2f} vs {self.reference_threshold}",
                "score": round(score, 3),
            }
        q = content_tokens(str(input.get("question", "")))
        score = overlap_ratio(q, answer)
        passed = score >= self.relevance_threshold
        return {
            "pass": passed,
            "reason": f"question overlap {score:.2f} vs {self.relevance_threshold}",
            "score": round(score, 3),
        }

    def _context_relevance(self, input: dict, output: dict) -> dict:
        q = content_tokens(str(input.get("question", "")))
        ctx = content_tokens(" ".join(_context_texts(output)))
        score = overlap_ratio(q, ctx)
        passed = score >= self.relevance_threshold
        return {"pass": passed, "reason": f"question overlap {score:.2f}", "score": round(score, 3)}


_RUBRICS = {
    "faithfulness": (
        "Does the ANSWER contain only claims that are directly supported by the CONTEXT? "
        "Any claim not in the context, including plausible common knowledge, means FAIL."
    ),
    "answer_relevance": (
        "Does the ANSWER actually address the QUESTION (not a neighbouring topic)? If a "
        "REFERENCE answer is given, does the ANSWER convey the same key facts?"
    ),
    "context_relevance": (
        "Would the CONTEXT help answer the QUESTION? FAIL if it is about a different topic."
    ),
}


class LLMJudge:
    name = "llm"

    def __init__(self, client: LLMClient, *, model: str | None = None) -> None:
        self.client = client
        self.model = model

    def judge(
        self, criterion: str, input: dict, output: dict, reference: dict | None = None
    ) -> dict:
        if criterion not in _RUBRICS:
            raise ValueError(f"unknown criterion: {criterion}")
        context = "\n\n---\n\n".join(_context_texts(output))
        parts = [
            f"CRITERION: {criterion}\n{_RUBRICS[criterion]}",
            f"QUESTION:\n{input.get('question', '')}",
            f"CONTEXT:\n{context or '(none)'}",
            f"ANSWER:\n{_strip_citations(str(output.get('answer', '')))}",
        ]
        if reference and reference.get("answer"):
            parts.append(f"REFERENCE:\n{reference['answer']}")
        parts.append(
            'Reply with JSON only: {"pass": true|false, "reason": "<one sentence>"}. '
            "Be strict; when unsure, fail."
        )
        messages = [
            Message(role="system", content="You are a strict, binary evaluator."),
            Message(role="user", content="\n\n".join(parts)),
        ]
        resp = self.client.complete(messages, model=self.model, temperature=0.0, max_tokens=200)
        return parse_verdict(resp.text)


def parse_verdict(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            data = json.loads(match.group(0))
            return {"pass": bool(data.get("pass")), "reason": str(data.get("reason", ""))}
        except json.JSONDecodeError:
            pass
    lowered = text.lower()
    return {"pass": "pass" in lowered and "fail" not in lowered, "reason": text.strip()[:200]}


def get_judge(settings, client: LLMClient | None = None) -> Judge:
    """Lexical judge for the fake provider, LLM judge (JUDGE_MODEL) otherwise."""
    if settings.resolved_llm_provider() == "fake":
        return LexicalJudge()
    if client is None:
        from docs_rag.llm.factory import get_client

        client = get_client(settings, role="judge")
    return LLMJudge(client, model=settings.judge_model)
