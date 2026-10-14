"""OpenAI-compatible chat-completions backend, used for both OpenAI direct and OpenRouter."""

from __future__ import annotations

import json
import time
from typing import Any

from docs_rag.llm.base import LLMResponse, Message, ToolCall, ToolSpec, Usage

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _to_openai_messages(messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        item: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.role == "tool" and m.tool_call_id:
            item["tool_call_id"] = m.tool_call_id
        out.append(item)
    return out


def _to_openai_tools(tools: list[ToolSpec] | None) -> list[dict[str, Any]] | None:
    if not tools:
        return None
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            },
        }
        for t in tools
    ]


class OpenAICompatClient:
    """Chat completions with tools. ``provider`` is "openai" or "openrouter"."""

    def __init__(
        self,
        api_key: str,
        *,
        provider: str = "openai",
        default_model: str = "openai/gpt-4o-mini",
        base_url: str | None = None,
        site_url: str | None = None,
        app_name: str | None = None,
    ) -> None:
        from openai import OpenAI  # imported lazily so the fake path has no SDK cost

        headers: dict[str, str] = {}
        if provider == "openrouter":
            base_url = base_url or OPENROUTER_BASE_URL
            if site_url:
                headers["HTTP-Referer"] = site_url
            if app_name:
                headers["X-Title"] = app_name
        self.provider = provider
        self.default_model = default_model
        self._client = OpenAI(api_key=api_key, base_url=base_url, default_headers=headers or None)

    def resolve_model(self, model: str | None) -> str:
        name = model or self.default_model
        if self.provider == "openai" and "/" in name:
            # OpenRouter slugs such as "openai/gpt-4o" become bare ids for the direct API.
            name = name.split("/", 1)[1]
        return name

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        model_id = self.resolve_model(model)
        kwargs: dict[str, Any] = {
            "model": model_id,
            "messages": _to_openai_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        oa_tools = _to_openai_tools(tools)
        if oa_tools:
            kwargs["tools"] = oa_tools
        if self.provider == "openrouter":
            # Ask OpenRouter to include the billed cost in the usage block.
            kwargs["extra_body"] = {"usage": {"include": True}}
        start = time.perf_counter()
        resp = self._client.chat.completions.create(**kwargs)
        latency_ms = (time.perf_counter() - start) * 1000

        choice = resp.choices[0]
        text = choice.message.content or ""
        tool_calls: list[ToolCall] = []
        for tc in choice.message.tool_calls or []:
            raw = tc.function.arguments or "{}"
            try:
                args = json.loads(raw)
            except json.JSONDecodeError:
                args = {"_raw": raw}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

        usage = resp.usage
        reported_cost = None
        if usage is not None:
            # OpenRouter puts `cost` on the usage object; the SDK keeps unknown fields.
            extra = getattr(usage, "model_extra", None) or {}
            cost = extra.get("cost", getattr(usage, "cost", None))
            if isinstance(cost, int | float):
                reported_cost = float(cost)
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ),
            model=resp.model or model_id,
            latency_ms=latency_ms,
            stop_reason=choice.finish_reason or "stop",
            reported_cost_usd=reported_cost,
        )
