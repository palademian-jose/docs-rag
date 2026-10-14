"""Deterministic fake LLM backend.

Three behaviours, in priority order:

1. Scripted: ``FakeLLMClient(responses=[...])`` returns the queued responses in order. A queued
   item can be a string, an ``LLMResponse`` or a dict ``{"tool": name, "arguments": {...}}`` which
   becomes a tool call. This is how tests drive tool use and judge verdicts.
2. Extractive RAG: when the prompt contains context chunks (see ``generation.prompt``), the fake
   picks the sentences with the highest lexical overlap with the question, emits ``[chunk_id]``
   citations and refuses with ``NOT_IN_DOCS`` when the best overlap is below a threshold.
3. Echo: otherwise it returns a short deterministic acknowledgement of the last user message.

The whole demo, eval and test-suite run on this backend when no API key is present.
"""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass

from docs_rag.generation.prompt import REFUSAL_TOKEN, ContextChunk, parse_context
from docs_rag.llm.base import LLMResponse, Message, ToolCall, ToolSpec, Usage, approx_tokens
from docs_rag.textutil import content_tokens, overlap_ratio, split_sentences

FAKE_MODEL = "fake-extractive-v1"


@dataclass(frozen=True)
class _Candidate:
    chunk: ContextChunk
    sentence: str
    score: float


class FakeLLMClient:
    provider = "fake"

    def __init__(
        self,
        responses: list[str | dict | LLMResponse] | None = None,
        *,
        refusal_threshold: float = 0.34,
        max_sentences: int = 3,
        model: str = FAKE_MODEL,
    ) -> None:
        self._queue: deque[str | dict | LLMResponse] = deque(responses or [])
        self.refusal_threshold = refusal_threshold
        self.max_sentences = max_sentences
        self.model = model
        self.calls: list[list[Message]] = []

    # -- public API ---------------------------------------------------------------------------
    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        start = time.perf_counter()
        self.calls.append(messages)
        prompt_text = "\n".join(m.text() for m in messages)
        in_tokens = approx_tokens(prompt_text)

        if self._queue:
            response = self._materialise(self._queue.popleft(), in_tokens, model)
        else:
            question, chunks = parse_context(prompt_text)
            if chunks and question:
                text = self._extractive_answer(question, chunks)
            elif tools:
                tool = tools[0]
                call = ToolCall(id="call_fake_1", name=tool.name, arguments={})
                response = LLMResponse(
                    text="",
                    tool_calls=[call],
                    usage=Usage(input_tokens=in_tokens, output_tokens=8),
                    model=model or self.model,
                    stop_reason="tool_use",
                )
                response.latency_ms = (time.perf_counter() - start) * 1000
                return response
            else:
                last_user = next((m.text() for m in reversed(messages) if m.role == "user"), "")
                text = f"[fake] {last_user[:200]}"
            response = LLMResponse(
                text=text,
                usage=Usage(input_tokens=in_tokens, output_tokens=approx_tokens(text)),
                model=model or self.model,
            )
        response.latency_ms = (time.perf_counter() - start) * 1000
        return response

    # -- helpers ------------------------------------------------------------------------------
    def _materialise(
        self, item: str | dict | LLMResponse, in_tokens: int, model: str | None
    ) -> LLMResponse:
        if isinstance(item, LLMResponse):
            return item.model_copy()
        if isinstance(item, dict):
            call = ToolCall(
                id=item.get("id", "call_fake_1"),
                name=item["tool"],
                arguments=item.get("arguments", {}),
            )
            return LLMResponse(
                text=item.get("text", ""),
                tool_calls=[call],
                usage=Usage(input_tokens=in_tokens, output_tokens=approx_tokens(json.dumps(item))),
                model=model or self.model,
                stop_reason="tool_use",
            )
        return LLMResponse(
            text=item,
            usage=Usage(input_tokens=in_tokens, output_tokens=approx_tokens(item)),
            model=model or self.model,
        )

    def _extractive_answer(self, question: str, chunks: list[ContextChunk]) -> str:
        q_tokens = content_tokens(question)
        if not q_tokens:
            return REFUSAL_TOKEN
        candidates: list[_Candidate] = []
        for chunk in chunks:
            chunk_overlap = overlap_ratio(q_tokens, content_tokens(chunk.text))
            for sentence in split_sentences(chunk.text):
                s_overlap = overlap_ratio(q_tokens, content_tokens(sentence))
                score = 0.65 * s_overlap + 0.35 * chunk_overlap
                candidates.append(_Candidate(chunk, sentence, score))
        if not candidates:
            return REFUSAL_TOKEN
        candidates.sort(key=lambda c: (-c.score, c.chunk.chunk_id, c.sentence))
        best = candidates[0]
        if best.score < self.refusal_threshold:
            return REFUSAL_TOKEN
        chosen: list[_Candidate] = []
        seen: set[str] = set()
        for cand in candidates:
            if cand.score < max(self.refusal_threshold, best.score * 0.8):
                break
            if cand.sentence in seen:
                continue
            seen.add(cand.sentence)
            chosen.append(cand)
            if len(chosen) >= self.max_sentences:
                break
        parts: list[str] = []
        for c in chosen:
            sentence = c.sentence.rstrip().rstrip(":;,")
            if sentence and sentence[-1] not in ".!?":
                sentence += "."
            parts.append(f"{sentence} [{c.chunk.chunk_id}]")
        return " ".join(parts)
