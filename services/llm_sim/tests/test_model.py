from __future__ import annotations

import random

import pytest

from llm_sim import model
from llm_sim.schemas import ChatMessage, FunctionDef, ToolDef


@pytest.mark.parametrize(
    ("used", "budget", "context", "expected"),
    [
        (0, 100, 100, True),
        (0, 100, 101, False),
        (50, 100, 50, True),
        (50, 100, 51, False),
    ],
)
def test_can_admit_boundary(used: int, budget: int, context: int, expected: bool) -> None:
    assert model.can_admit(used, budget, context) is expected


def test_prefill_seconds_scales_linearly_with_prompt_tokens() -> None:
    short = model.compute_prefill_seconds(100, prefill_tokens_per_second=100.0)
    long = model.compute_prefill_seconds(400, prefill_tokens_per_second=100.0)
    assert long == pytest.approx(4 * short)


def test_inter_token_latency_scales_with_concurrent_running_requests() -> None:
    one = model.compute_inter_token_latency_seconds(1, decode_tokens_per_second_total=100.0)
    four = model.compute_inter_token_latency_seconds(4, decode_tokens_per_second_total=100.0)
    assert four == pytest.approx(4 * one)
    assert four > one  # the "noisy neighbour" mechanic


def test_compute_output_tokens_honors_explicit_max_tokens() -> None:
    rng = random.Random(0)
    assert model.compute_output_tokens(42, rng, 1, 1000) == 42


def test_compute_output_tokens_is_deterministic_under_seed() -> None:
    rng_a = random.Random(7)
    rng_b = random.Random(7)
    sequence_a = [model.compute_output_tokens(None, rng_a, 10, 20) for _ in range(5)]
    sequence_b = [model.compute_output_tokens(None, rng_b, 10, 20) for _ in range(5)]
    assert sequence_a == sequence_b
    assert all(10 <= v <= 20 for v in sequence_a)


def test_estimate_prompt_tokens_scales_with_message_length() -> None:
    short = model.estimate_prompt_tokens([ChatMessage(role="user", content="hi")], None)
    long = model.estimate_prompt_tokens([ChatMessage(role="user", content="hi " * 50)], None)
    assert long > short


def test_estimate_prompt_tokens_counts_tool_definitions() -> None:
    tools = [ToolDef(function=FunctionDef(name="search", description="search the web"))]
    without_tools = model.estimate_prompt_tokens([ChatMessage(role="user", content="hi")], None)
    with_tools = model.estimate_prompt_tokens([ChatMessage(role="user", content="hi")], tools)
    assert with_tools > without_tools
