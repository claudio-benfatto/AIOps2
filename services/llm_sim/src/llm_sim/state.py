from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from llm_sim import model

# vLLM-shape latency buckets (seconds). Real vLLM publishes different bucket
# sets per-metric (TTFT vs TPOT vs e2e); we use one shared latency-spanning
# set for all three histograms here as a documented simplification — the
# shape is taken from the task's suggested vLLM-like buckets, not derived
# from a specific vLLM release's exact per-metric config.
LATENCY_BUCKETS: tuple[float, ...] = (
    0.001,
    0.005,
    0.01,
    0.02,
    0.04,
    0.06,
    0.08,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    7.5,
    10.0,
    20.0,
    40.0,
    80.0,
    160.0,
    640.0,
    2560.0,
)


@dataclass
class HistogramSink:
    """Cumulative bucket counts for one histogram, observed in place.

    `cumulative_counts[i]` is the count of observations <= `buckets[i]`
    (standard Prometheus cumulative-histogram semantics). `count`/`sum`
    track the implicit +Inf bucket and the total, respectively.
    """

    buckets: tuple[float, ...] = LATENCY_BUCKETS
    cumulative_counts: list[int] = field(default_factory=lambda: [0] * len(LATENCY_BUCKETS))
    sum: float = 0.0
    count: int = 0

    def observe(self, value: float) -> None:
        self.count += 1
        self.sum += value
        for i, le in enumerate(self.buckets):
            if value <= le:
                self.cumulative_counts[i] += 1


class SimulationState:
    """Owns every value the /metrics exporter reads. Only mechanics (admit,
    release, record_completion) mutate it — see docs/adr/0009.

    KV budget is reserved for `prompt_tokens` at admission and released only
    on completion (not grown mid-request during decode) — a literal reading
    of the admission formula `kv_cache_used_tokens + request_context_tokens`
    using only prompt-derived context. Revisit if a later scenario needs
    mid-request KV growth fidelity.
    """

    def __init__(self, *, kv_cache_budget_tokens: int) -> None:
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition(self._lock)

        self.kv_cache_budget_tokens = kv_cache_budget_tokens
        self.num_requests_running = 0
        self.num_requests_waiting = 0
        self.kv_cache_used_tokens = 0
        self.prompt_tokens_total = 0
        self.generation_tokens_total = 0

        self.ttft_seconds = HistogramSink()
        self.inter_token_latency_seconds = HistogramSink()
        self.e2e_request_latency_seconds = HistogramSink()

    async def admit(self, context_tokens: int) -> None:
        """Block until `context_tokens` of KV budget is available, then
        reserve it and count this request as running. Queueing time is real
        wall-clock time: `Condition.wait_for` suspends this coroutine until
        another request's `release()` frees enough budget and notifies."""
        async with self._condition:
            if not model.can_admit(
                self.kv_cache_used_tokens, self.kv_cache_budget_tokens, context_tokens
            ):
                self.num_requests_waiting += 1
                try:
                    await self._condition.wait_for(
                        lambda: model.can_admit(
                            self.kv_cache_used_tokens,
                            self.kv_cache_budget_tokens,
                            context_tokens,
                        )
                    )
                finally:
                    self.num_requests_waiting -= 1
            self.kv_cache_used_tokens += context_tokens
            self.num_requests_running += 1

    async def release(self, context_tokens: int) -> None:
        """Free `context_tokens` of KV budget and wake any waiters."""
        async with self._condition:
            self.kv_cache_used_tokens -= context_tokens
            self.num_requests_running -= 1
            self._condition.notify_all()

    async def running_count(self) -> int:
        async with self._lock:
            return self.num_requests_running

    async def record_completion(
        self,
        *,
        prompt_tokens: int,
        generation_tokens: int,
        ttft_seconds: float,
        inter_token_latency_seconds: float,
        e2e_seconds: float,
    ) -> None:
        async with self._lock:
            self.prompt_tokens_total += prompt_tokens
            self.generation_tokens_total += generation_tokens
            self.ttft_seconds.observe(ttft_seconds)
            self.inter_token_latency_seconds.observe(inter_token_latency_seconds)
            self.e2e_request_latency_seconds.observe(e2e_seconds)
