from __future__ import annotations

import random
from collections.abc import Sequence

from llm_sim.schemas import ChatMessage, ToolDef


def can_admit(kv_cache_used_tokens: int, kv_cache_budget_tokens: int, context_tokens: int) -> bool:
    """KV-budget-only admission control (no separate max-batch-size knob)."""
    return kv_cache_used_tokens + context_tokens <= kv_cache_budget_tokens


def compute_prefill_seconds(prompt_tokens: int, prefill_tokens_per_second: float) -> float:
    if prefill_tokens_per_second <= 0:
        raise ValueError("prefill_tokens_per_second must be positive")
    return prompt_tokens / prefill_tokens_per_second


def compute_inter_token_latency_seconds(
    num_requests_running: int, decode_tokens_per_second_total: float
) -> float:
    """Shared decode throughput divided across concurrently running
    requests — this is the "noisy neighbour" mechanic: more concurrent
    requests directly raises everyone's per-token latency."""
    if decode_tokens_per_second_total <= 0:
        raise ValueError("decode_tokens_per_second_total must be positive")
    return num_requests_running / decode_tokens_per_second_total


def compute_output_tokens(
    requested_max_tokens: int | None,
    rng: random.Random,
    min_tokens: int,
    max_tokens: int,
) -> int:
    """The only place actual randomness enters the simulator (invariant 5)."""
    if requested_max_tokens is not None:
        return requested_max_tokens
    return rng.randint(min_tokens, max_tokens)


def estimate_prompt_tokens(messages: Sequence[ChatMessage], tools: Sequence[ToolDef] | None) -> int:
    """Approximate, deterministic whitespace-based tokenization.

    No real tokenizer is in scope for a latency/queueing simulator — the
    exact count doesn't matter, only that it scales with input size, which
    is what the prefill-cost and KV-admission mechanics need.
    """
    text_parts = [m.content or "" for m in messages]
    if tools:
        text_parts.extend(t.function.name for t in tools)
        text_parts.extend(t.function.description or "" for t in tools)
    word_count = len(" ".join(text_parts).split())
    return max(1, word_count)
