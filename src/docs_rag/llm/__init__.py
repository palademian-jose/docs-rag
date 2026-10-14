"""LLM provider abstraction (fake, openrouter, anthropic, openai).

``get_client`` and ``FakeLLMClient`` are loaded lazily so that importing the contract types from
``docs_rag.llm`` never pulls in the backends (which depend on the prompt module).
"""

from __future__ import annotations

from typing import Any

from docs_rag.llm.base import LLMClient, LLMResponse, Message, ToolCall, ToolSpec, Usage

__all__ = [
    "FakeLLMClient",
    "LLMClient",
    "LLMResponse",
    "Message",
    "ToolCall",
    "ToolSpec",
    "Usage",
    "get_client",
]


def __getattr__(name: str) -> Any:
    if name == "get_client":
        from docs_rag.llm.factory import get_client

        return get_client
    if name == "FakeLLMClient":
        from docs_rag.llm.fake import FakeLLMClient

        return FakeLLMClient
    raise AttributeError(name)
