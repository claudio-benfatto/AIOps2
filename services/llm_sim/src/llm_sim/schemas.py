from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolCallFunction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    arguments: str = "{}"  # JSON-encoded string, OpenAI convention


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    type: Literal["function"] = "function"
    function: ToolCallFunction


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class FunctionDef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolDef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["function"] = "function"
    function: FunctionDef


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str
    messages: list[ChatMessage]
    tools: list[ToolDef] | None = None
    max_tokens: int | None = None
    temperature: float | None = None


class Usage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    message: ChatMessage
    finish_reason: Literal["stop", "tool_calls"]


class ChatCompletionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: Usage
