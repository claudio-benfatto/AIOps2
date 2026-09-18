from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, NamedTuple

from llm_sim.schemas import ChatMessage, ToolCall, ToolCallFunction, ToolDef


class PolicyResult(NamedTuple):
    message: ChatMessage
    finish_reason: Literal["stop", "tool_calls"]


def decide_response(
    messages: Sequence[ChatMessage],
    tools: Sequence[ToolDef] | None,
    *,
    request_id: int,
) -> PolicyResult:
    """Minimal, tool-agnostic response stub (PLAN.md decision #2 scope cut).

    If `tools` is present and no tool has been called yet in this
    conversation, pick the first listed tool with empty arguments. No tool
    names are hardcoded — agent-svc's real tools don't exist yet (M1.2).
    Deterministic tool_call id (derived from request_id, not uuid4) to keep
    every part of the response reproducible under a seed.
    """
    if tools and not _tool_already_called(messages):
        first_tool = tools[0]
        call = ToolCall(
            id=f"call_{request_id}",
            function=ToolCallFunction(name=first_tool.function.name, arguments="{}"),
        )
        message = ChatMessage(role="assistant", content=None, tool_calls=[call])
        return PolicyResult(message=message, finish_reason="tool_calls")

    message = ChatMessage(role="assistant", content="This is a synthetic llm-sim response.")
    return PolicyResult(message=message, finish_reason="stop")


def _tool_already_called(messages: Sequence[ChatMessage]) -> bool:
    return any((m.role == "assistant" and m.tool_calls) or m.role == "tool" for m in messages)
