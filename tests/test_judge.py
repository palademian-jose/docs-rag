from __future__ import annotations

import pytest

from docs_rag.evals.judge import LexicalJudge, LLMJudge, get_judge, parse_verdict
from docs_rag.llm import FakeLLMClient
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


def test_parse_verdict_variants() -> None:
    assert parse_verdict('{"pass": true, "reason": "ok"}') == {"pass": True, "reason": "ok"}
    assert parse_verdict('Sure: {"pass": false, "reason": "nope"} done')["pass"] is False
    assert parse_verdict("PASS - looks good")["pass"] is True
    assert parse_verdict("this is a FAIL")["pass"] is False


def test_llm_judge_uses_scripted_client() -> None:
    client = FakeLLMClient(responses=['{"pass": false, "reason": "claim not in context"}'])
    judge = LLMJudge(client, model="openai/gpt-4.1-mini")
    verdict = judge.judge("faithfulness", Q, {"answer": "x", "context": CONTEXT}, {"answer": "y"})
    assert verdict == {"pass": False, "reason": "claim not in context"}
    prompt = client.calls[0][1].text()
    assert "CRITERION: faithfulness" in prompt and "REFERENCE" in prompt
    with pytest.raises(ValueError):
        judge.judge("vibes", Q, {})


def test_get_judge_picks_lexical_for_fake() -> None:
    assert isinstance(get_judge(Settings(llm_provider="fake")), LexicalJudge)
    llm_judge = get_judge(
        Settings(llm_provider="openrouter", openrouter_api_key="k"), client=FakeLLMClient()
    )
    assert isinstance(llm_judge, LLMJudge)
