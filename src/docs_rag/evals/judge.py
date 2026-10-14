"""Judge interface (PLAN.md shared contract 4).

``judge(criterion, input, output, reference) -> {"pass": bool, "reason": str}``

Criteria:
- ``faithfulness``: every claim in ``output["answer"]`` is supported by ``output["context"]``.
- ``answer_relevance``: the answer addresses ``input["question"]`` (and matches
  ``reference["answer"]`` when given).
- ``context_relevance``: ``output["context"]`` (one chunk) is useful for the question.

Two implementations: ``LexicalJudge`` (deterministic token-overlap heuristics, used with the
fake provider and in CI) and ``EvalkitJudge``, which routes each criterion to
``evalkit.judge.Judge`` from llm-evalops (criterion prompt, strict ``{"pass", "reason"}`` JSON,
one repair turn) on ``JUDGE_MODEL``. The lexical judge is kept for the fake provider because
evalkit's fake judge is a different heuristic, and swapping it would move the committed
fake-provider baseline and the hand-label calibration numbers for no new information.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from docs_rag.generation.answer import CITATION_RE
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


class EvalkitJudge:
    """Adapter from docs-rag's judge shape to ``evalkit.judge.Judge`` (contract 4).

    docs-rag passes ``output={"answer", "context": [chunk texts]}``; evalkit's templates read
    ``input`` / ``output`` / ``reference``. The mapping per criterion:

    - ``faithfulness``: output = the answer (citations stripped), reference = the context chunks
    - ``answer_relevance``: output = the answer, reference = the gold answer when there is one
    - ``context_relevance``: output = the passage(s) to grade
    """

    name = "evalkit"

    def __init__(self, client: Any | None = None, *, model: str | None = None) -> None:
        self.client = client
        self.model = model
        self._judges: dict[str, Any] = {}

    def _judge_for(self, criterion: str) -> Any:
        if criterion not in self._judges:
            from evalkit.judge import Judge as EvalkitCriterionJudge

            self._judges[criterion] = EvalkitCriterionJudge(
                criterion, self.client, model=self.model
            )
        return self._judges[criterion]

    def judge(
        self, criterion: str, input: dict, output: dict, reference: dict | None = None
    ) -> dict:
        if criterion not in CRITERIA:
            raise ValueError(f"unknown criterion: {criterion}")
        question = {"question": str(input.get("question", ""))}
        answer = _strip_citations(str(output.get("answer", "")))
        contexts = [t for t in _context_texts(output) if t]
        if criterion == "faithfulness":
            args: tuple[dict, dict | None] = ({"answer": answer}, {"contexts": contexts})
        elif criterion == "answer_relevance":
            gold = reference if reference and reference.get("answer") else None
            args = ({"answer": answer}, gold)
        else:
            args = ({"passage": "\n\n".join(contexts)}, None)
        return self._judge_for(criterion).judge(question, *args)


def get_judge(settings, client: Any | None = None) -> Judge:
    """Lexical judge for the fake provider, evalkit's LLM judge (JUDGE_MODEL) otherwise.

    ``client`` is an llmops-style client (``complete(messages, model=...)``); by default one is
    built from the settings (provider, key and model ids) with ``llmops.llm.get_client``.
    """
    if settings.resolved_llm_provider() == "fake":
        return LexicalJudge()
    from evalkit.judge import check_family

    check_family(settings.llm_model, settings.judge_model, strict=False)
    if client is None:
        client = _llmops_client(settings)
    return EvalkitJudge(client, model=settings.judge_model)


def _llmops_client(settings) -> Any:
    from llmops.llm import get_client
    from llmops.settings import Settings as LlmopsSettings

    return get_client(
        LlmopsSettings(
            llm_provider=settings.resolved_llm_provider(),
            llm_model=settings.llm_model,
            judge_model=settings.judge_model,
            cheap_model=settings.cheap_model,
            openrouter_api_key=settings.openrouter_api_key,
            openrouter_base_url=settings.openrouter_base_url,
            openrouter_site_url=settings.openrouter_site_url,
            openrouter_app_name=settings.openrouter_app_name,
            anthropic_api_key=settings.anthropic_api_key,
            openai_api_key=settings.openai_api_key,
        ),
        role="judge",
    )
