from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from llm_sim.api import create_app
from llm_sim.config import Settings


@pytest.fixture
def client() -> TestClient:
    fast_settings = Settings(
        seed=42,
        kv_cache_budget_tokens=1_000_000,
        prefill_tokens_per_second=1_000_000_000.0,
        decode_tokens_per_second_total=1_000_000_000.0,
        default_min_output_tokens=4,
        default_max_output_tokens=8,
    )
    app = create_app(fast_settings)
    return TestClient(app)


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_completions_plain_text_when_no_tools(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/completions",
        json={"model": "llm-sim", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["finish_reason"] == "stop"
    assert body["choices"][0]["message"]["content"]
    assert body["choices"][0]["message"]["tool_calls"] is None
    assert body["usage"]["prompt_tokens"] > 0
    assert body["usage"]["completion_tokens"] > 0
    assert body["usage"]["total_tokens"] == (
        body["usage"]["prompt_tokens"] + body["usage"]["completion_tokens"]
    )


def test_chat_completions_picks_first_tool_when_tools_present(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "llm-sim",
            "messages": [{"role": "user", "content": "search for something"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "search", "description": "search the web"},
                },
                {
                    "type": "function",
                    "function": {"name": "retrieve", "description": "retrieve docs"},
                },
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["finish_reason"] == "tool_calls"
    tool_calls = body["choices"][0]["message"]["tool_calls"]
    assert tool_calls is not None
    assert tool_calls[0]["function"]["name"] == "search"
    assert body["choices"][0]["message"]["content"] is None


def test_chat_completions_answers_text_after_tool_result_present(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "llm-sim",
            "messages": [
                {"role": "user", "content": "search for something"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "call_1", "function": {"name": "search", "arguments": "{}"}}
                    ],
                },
                {"role": "tool", "tool_call_id": "call_1", "content": "results here"},
            ],
            "tools": [{"type": "function", "function": {"name": "search"}}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["finish_reason"] == "stop"
    assert body["choices"][0]["message"]["tool_calls"] is None


def test_chat_completions_malformed_request_returns_4xx(client: TestClient) -> None:
    response = client.post("/v1/chat/completions", json={"model": "llm-sim"})  # missing messages
    assert 400 <= response.status_code < 500


def test_metrics_endpoint_exposes_vllm_prefixed_series(client: TestClient) -> None:
    client.post(
        "/v1/chat/completions",
        json={"model": "llm-sim", "messages": [{"role": "user", "content": "hello"}]},
    )
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text
    for name in (
        "vllm:num_requests_running",
        "vllm:num_requests_waiting",
        "vllm:kv_cache_usage_perc",
        "vllm:prompt_tokens_total",
        "vllm:generation_tokens_total",
        "vllm:time_to_first_token_seconds",
        "vllm:inter_token_latency_seconds",
        "vllm:e2e_request_latency_seconds",
    ):
        assert name in text, f"{name} missing from /metrics output"
    assert "vllm:prompt_tokens_total_total" not in text  # guards the CounterMetricFamily footgun


def test_metrics_move_after_a_request(client: TestClient) -> None:
    before = client.get("/metrics").text
    client.post(
        "/v1/chat/completions",
        json={"model": "llm-sim", "messages": [{"role": "user", "content": "hello there"}]},
    )
    after = client.get("/metrics").text
    assert before != after  # prompt_tokens_total / generation_tokens_total must have moved
