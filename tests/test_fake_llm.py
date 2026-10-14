from __future__ import annotations

from docs_rag.generation.prompt import REFUSAL_TOKEN, ContextChunk, build_messages, parse_context
from docs_rag.llm import FakeLLMClient, LLMClient, Message, ToolSpec
from docs_rag.llm.factory import get_client
from docs_rag.settings import Settings

CHUNKS = [
    ContextChunk(
        "aaaaaa0001",
        "deploy.md",
        10,
        14,
        "## Canary analysis\n\nProduction deploys start with a canary that receives 5% of "
        "traffic for ten minutes. The canary is promoted automatically when checks pass.",
    ),
    ContextChunk(
        "bbbbbb0002",
        "cats.md",
        1,
        3,
        "## Cats\n\nCats sleep sixteen hours a day. They purr when content.",
    ),
]


def test_prompt_roundtrip() -> None:
    messages = build_messages("How long does the canary run?", CHUNKS)
    question, chunks = parse_context(messages[1].text())
    assert question == "How long does the canary run?"
    assert [c.chunk_id for c in chunks] == ["aaaaaa0001", "bbbbbb0002"]
    assert chunks[0].start_line == 10 and chunks[0].end_line == 14


def test_extractive_answer_cites_best_chunk() -> None:
    llm = FakeLLMClient()
    resp = llm.complete(build_messages("How long does the canary receive traffic?", CHUNKS))
    assert "[aaaaaa0001]" in resp.text
    assert "[bbbbbb0002]" not in resp.text
    assert "ten minutes" in resp.text
    assert resp.usage.input_tokens > 0 and resp.usage.output_tokens > 0
    assert resp.model == llm.model


def test_extractive_refuses_when_overlap_is_low() -> None:
    llm = FakeLLMClient()
    resp = llm.complete(build_messages("What is the capital of France?", CHUNKS))
    assert resp.text == REFUSAL_TOKEN


def test_scripted_responses_and_tool_calls() -> None:
    llm = FakeLLMClient(responses=["first", {"tool": "lookup", "arguments": {"q": "x"}}])
    tool = ToolSpec(
        name="lookup",
        description="look",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    )
    r1 = llm.complete([Message(role="user", content="hi")])
    assert r1.text == "first" and r1.tool_calls == []
    r2 = llm.complete([Message(role="user", content="hi")], tools=[tool])
    assert r2.tool_calls[0].name == "lookup"
    assert r2.tool_calls[0].arguments == {"q": "x"}
    assert r2.stop_reason == "tool_use"
    # heuristic tool call when nothing is scripted
    r3 = llm.complete([Message(role="user", content="hi")], tools=[tool])
    assert r3.tool_calls and r3.tool_calls[0].name == "lookup"


def test_factory_defaults_to_fake_without_keys() -> None:
    settings = Settings(
        llm_provider=None, openrouter_api_key=None, anthropic_api_key=None, openai_api_key=None
    )
    client = get_client(settings)
    assert isinstance(client, LLMClient)
    assert client.provider == "fake"
    assert settings.resolved_llm_provider() == "fake"


def test_provider_resolution_prefers_openrouter() -> None:
    s = Settings(llm_provider=None, openrouter_api_key="k", openai_api_key="k2")
    assert s.resolved_llm_provider() == "openrouter"
    s2 = Settings(llm_provider=None, openai_api_key="k2")
    assert s2.resolved_llm_provider() == "openai"
    s3 = Settings(llm_provider="fake", openrouter_api_key="k")
    assert s3.resolved_llm_provider() == "fake"


def test_openai_compat_model_resolution() -> None:
    from docs_rag.llm.openai_compat import OpenAICompatClient

    direct = OpenAICompatClient("k", provider="openai", default_model="openai/gpt-4o-mini")
    assert direct.resolve_model(None) == "gpt-4o-mini"
    router = OpenAICompatClient(
        "k", provider="openrouter", default_model="anthropic/claude-sonnet-4.5"
    )
    assert router.resolve_model(None) == "anthropic/claude-sonnet-4.5"


def test_anthropic_model_resolution() -> None:
    from docs_rag.llm.anthropic_client import AnthropicClient

    client = AnthropicClient("k", default_model="anthropic/claude-sonnet-4.5")
    assert client.resolve_model(None) == "claude-sonnet-4-5"
    assert client.resolve_model("claude-haiku-4-5") == "claude-haiku-4-5"
