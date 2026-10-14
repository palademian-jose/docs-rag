from __future__ import annotations

import pytest
from llmops.llm import FakeClient, LLMResponse

from docs_rag.evals.judge import EvalkitJudge, LexicalJudge, get_judge
from docs_rag.settings import Settings

CONTEXT = [
    "Production deploys start with a canary that receives 5% of traffic for ten minutes. "
    "The canary is promoted automatically when all checks pass."
]
Q = {"question": "How long does the canary receive traffic?"}


def test_lexical_faithfulness_passes_supported_answer() -> None:
    judge = LexicalJudge()
    out = {
        "answer": "The canary receives 5% of traffic for ten minutes. [abcdef1234]",
        "context": CONTEXT,
    }
    verdict = judge.judge("faithfulness", Q, out)
    assert verdict["pass"] is True
    assert "reason" in verdict


def test_lexical_faithfulness_fails_unsupported_claim() -> None:
    judge = LexicalJudge()
    out = {
        "answer": "The canary runs for ten minutes. Deploys require a signed waiver from legal.",
        "context": CONTEXT,
    }
    verdict = judge.judge("faithfulness", Q, out)
    assert verdict["pass"] is False
    assert "waiver" in verdict["reason"]
    assert judge.judge("faithfulness", Q, {"answer": "", "context": CONTEXT})["pass"] is False
    assert judge.judge("faithfulness", Q, {"answer": "x y z", "context": []})["pass"] is False


def test_lexical_answer_relevance_with_and_without_reference() -> None:
    judge = LexicalJudge()
    out = {"answer": "The canary receives 5% of traffic for ten minutes."}
    assert judge.judge("answer_relevance", Q, out)["pass"] is True
    ref = {"answer": "The canary receives traffic for ten minutes before promotion."}
    assert judge.judge("answer_relevance", Q, out, ref)["pass"] is True
    off = {"answer": "Cats sleep sixteen hours a day."}
    assert judge.judge("answer_relevance", Q, off, ref)["pass"] is False


def test_lexical_context_relevance_and_unknown_criterion() -> None:
    judge = LexicalJudge()
    assert judge.judge("context_relevance", Q, {"context": CONTEXT})["pass"] is True
    assert judge.judge("context_relevance", Q, {"context": "cats purr"})["pass"] is False
    with pytest.raises(ValueError):
        judge.judge("vibes", Q, {})


class _ScriptedClient:
    """Minimal llmops-style client: returns queued texts and records the prompts it saw."""

    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.prompts: list[str] = []

    def complete(self, messages, *, tools=None, model=None, temperature=0.0, max_tokens=1024):
        self.prompts.append("\n".join(m.text() for m in messages))
        return LLMResponse(text=self.texts.pop(0), model=model or "stub")


def test_evalkit_judge_maps_docs_rag_fields_onto_evalkit_prompts() -> None:
    client = _ScriptedClient('{"pass": false, "reason": "claim not in context"}')
    judge = EvalkitJudge(client, model="openai/gpt-4.1-mini")
    out = {"answer": "The canary runs for an hour. [abcdef1234]", "context": CONTEXT}
    verdict = judge.judge("faithfulness", Q, out)
    assert verdict == {"pass": False, "reason": "claim not in context"}
    prompt = client.prompts[0]
    assert "<criterion>faithfulness</criterion>" in prompt
    assert "How long does the canary receive traffic?" in prompt
    assert "The canary runs for an hour." in prompt and "[abcdef1234]" not in prompt
    assert CONTEXT[0] in prompt, "the context chunks travel as the reference"
    with pytest.raises(ValueError):
        judge.judge("vibes", Q, {})


def test_evalkit_judge_uses_gold_answer_and_passages_for_the_other_criteria() -> None:
    client = _ScriptedClient(
        '{"pass": true, "reason": "on topic"}', '{"pass": true, "reason": "ok"}'
    )
    judge = EvalkitJudge(client)
    out = {"answer": "Ten minutes.", "context": CONTEXT}
    assert judge.judge("answer_relevance", Q, out, {"answer": "Ten minutes of canary."})["pass"]
    assert judge.judge("context_relevance", Q, out)["pass"]
    assert "<criterion>answer_relevance</criterion>" in client.prompts[0]
    assert "<criterion>context_relevance</criterion>" in client.prompts[1]
    assert CONTEXT[0] in client.prompts[1]


def test_evalkit_judge_repairs_one_malformed_verdict() -> None:
    client = _ScriptedClient("PASS, looks fine", '{"pass": true, "reason": "fixed"}')
    verdict = EvalkitJudge(client).judge("faithfulness", Q, {"answer": "x y", "context": CONTEXT})
    assert verdict == {"pass": True, "reason": "fixed"} and len(client.prompts) == 2


def test_evalkit_judge_with_llmops_fake_client_end_to_end() -> None:
    judge = EvalkitJudge(FakeClient())
    good = {"answer": "The canary receives 5% of traffic for ten minutes.", "context": CONTEXT}
    bad = {"answer": "Deploys require a signed waiver from legal counsel.", "context": CONTEXT}
    assert judge.judge("faithfulness", Q, good)["pass"] is True
    assert judge.judge("faithfulness", Q, bad)["pass"] is False


def test_get_judge_picks_lexical_for_fake_and_evalkit_otherwise() -> None:
    assert isinstance(get_judge(Settings(llm_provider="fake")), LexicalJudge)
    judge = get_judge(
        Settings(llm_provider="openrouter", openrouter_api_key="k"), client=_ScriptedClient()
    )
    assert isinstance(judge, EvalkitJudge) and judge.model == "openai/gpt-4.1-mini"


def test_get_judge_builds_an_llmops_client_from_docs_rag_settings() -> None:
    settings = Settings(
        llm_provider="openrouter", openrouter_api_key="k", judge_model="openai/gpt-4.1-mini"
    )
    judge = get_judge(settings)
    assert isinstance(judge, EvalkitJudge)
    assert type(judge.client).__name__ == "OpenRouterClient"
