"""Shared LLM provider contract (PLAN.md, shared contract 1)."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict]
    tool_call_id: str | None = None

    def text(self) -> str:
        """Flatten content to plain text (joins text blocks when content is a list)."""
        if isinstance(self.content, str):
            return self.content
        parts: list[str] = []
        for block in self.content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict  # JSON Schema; additionalProperties should be false


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class LLMResponse(BaseModel):
    text: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    model: str
    latency_ms: float = 0.0
    stop_reason: str = "end_turn"
    # Provider-reported cost in USD when available (OpenRouter returns usage.cost).
    reported_cost_usd: float | None = None


@runtime_checkable
class LLMClient(Protocol):
    provider: str

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> LLMResponse: ...


def approx_tokens(text: str) -> int:
    """Cheap token estimate used by the fake backend (roughly 4 characters per token)."""
    return max(1, len(text) // 4)
