"""Anthropic Messages API backend with native tool use."""

from __future__ import annotations

import time
from typing import Any

from docs_rag.llm.base import LLMResponse, Message, ToolCall, ToolSpec, Usage


def _split_system(messages: list[Message]) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    out: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "system":
            system_parts.append(m.text())
        elif m.role == "tool":
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": m.tool_call_id,
                            "content": m.text(),
                        }
                    ],
                }
            )
        else:
            out.append({"role": m.role, "content": m.content})
    return "\n\n".join(system_parts), out


class AnthropicClient:
    provider = "anthropic"

    def __init__(self, api_key: str, *, default_model: str = "claude-sonnet-4-5") -> None:
        from anthropic import Anthropic

        self.default_model = default_model
        self._client = Anthropic(api_key=api_key)

    def resolve_model(self, model: str | None) -> str:
        name = model or self.default_model
        if (
            "/" in name
        ):  # OpenRouter slug -> bare Anthropic id (claude-sonnet-4.5 -> claude-sonnet-4-5)
            name = name.split("/", 1)[1].replace(".", "-")
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
        system, msgs = _split_system(messages)
        kwargs: dict[str, Any] = {
            "model": self.resolve_model(model),
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ]
        start = time.perf_counter()
        resp = self._client.messages.create(**kwargs)
        latency_ms = (time.perf_counter() - start) * 1000

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
                )
        return LLMResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens
            ),
            model=resp.model,
            latency_ms=latency_ms,
            stop_reason=resp.stop_reason or "end_turn",
        )
