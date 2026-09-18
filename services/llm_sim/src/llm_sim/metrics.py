from __future__ import annotations

from collections.abc import Iterable

from prometheus_client.core import Metric
from prometheus_client.registry import Collector
from prometheus_client.samples import Sample
from prometheus_client.utils import floatToGoString

from llm_sim.state import HistogramSink, SimulationState


class SimulationCollector(Collector):
    """Reads SimulationState at scrape time; never writes to it (ADR 0009).

    Built from the low-level `Metric`/`Sample` primitives rather than
    `prometheus_client`'s `CounterMetricFamily`/`HistogramMetricFamily`
    convenience classes: those apply version-sensitive auto-suffixing
    (`_total`, `_bucket`, `_sum`, `_count`) that risks silently producing
    `vllm:prompt_tokens_total_total` instead of the literal name required by
    README.md's metric table. Building samples by hand makes the exposed
    name 100% explicit and immune to that footgun.
    """

    def __init__(self, state: SimulationState) -> None:
        self._state = state

    def collect(self) -> Iterable[Metric]:
        state = self._state
        yield _gauge(
            "vllm:num_requests_running",
            "Number of requests currently running (prefill or decode).",
            state.num_requests_running,
        )
        yield _gauge(
            "vllm:num_requests_waiting",
            "Number of requests waiting for KV cache budget to free up.",
            state.num_requests_waiting,
        )
        usage_perc = (
            state.kv_cache_used_tokens / state.kv_cache_budget_tokens
            if state.kv_cache_budget_tokens
            else 0.0
        )
        yield _gauge(
            "vllm:kv_cache_usage_perc",
            "Fraction of the KV cache token budget currently in use.",
            usage_perc,
        )
        yield _counter(
            "vllm:prompt_tokens_total", "Total prefill tokens processed.", state.prompt_tokens_total
        )
        yield _counter(
            "vllm:generation_tokens_total",
            "Total decode tokens generated.",
            state.generation_tokens_total,
        )
        yield _histogram(
            "vllm:time_to_first_token_seconds",
            "Time to first token: queueing plus prefill latency.",
            state.ttft_seconds,
        )
        yield _histogram(
            "vllm:inter_token_latency_seconds",
            "Per-token decode latency.",
            state.inter_token_latency_seconds,
        )
        yield _histogram(
            "vllm:e2e_request_latency_seconds",
            "Full request latency from admission to last token.",
            state.e2e_request_latency_seconds,
        )


def _gauge(name: str, documentation: str, value: float) -> Metric:
    metric = Metric(name, documentation, "gauge")
    metric.samples = [Sample(name, {}, value)]
    return metric


def _counter(name: str, documentation: str, value: float) -> Metric:
    """`name` is the full literal counter name (e.g. "vllm:prompt_tokens_total").

    `generate_latest()` unconditionally appends "_total" to a counter
    Metric's *family* name (`metric.name`) when rendering the `# HELP`/
    `# TYPE` comment lines (see `prometheus_client.exposition`, the
    `mtype == "counter"` branch) — an OpenMetrics convention that assumes
    the family name excludes "_total". Since vLLM's literal metric names
    already include "_total", passing the full name straight through as the
    family would double-suffix those two comment lines to
    "..._total_total" (confirmed empirically against the installed
    prometheus_client version; the sample line itself is unaffected, since
    its name is set explicitly below). Stripping the suffix from the family
    name here makes generate_latest()'s own suffixing round-trip back to
    the literal name in the HELP/TYPE lines too.
    """
    family_name = name.removesuffix("_total")
    metric = Metric(family_name, documentation, "counter")
    metric.samples = [Sample(name, {}, value)]
    return metric


def _histogram(name: str, documentation: str, sink: HistogramSink) -> Metric:
    metric = Metric(name, documentation, "histogram")
    samples = [
        # prometheus_client.utils.floatToGoString has no type annotations
        # (despite the package shipping py.typed), so mypy sees it as
        # untyped even though it's a plain str -> str function.
        Sample(
            f"{name}_bucket",
            {"le": floatToGoString(le)},  # type: ignore[no-untyped-call]
            sink.cumulative_counts[i],
        )
        for i, le in enumerate(sink.buckets)
    ]
    samples.append(Sample(f"{name}_bucket", {"le": "+Inf"}, sink.count))
    samples.append(Sample(f"{name}_sum", {}, sink.sum))
    samples.append(Sample(f"{name}_count", {}, sink.count))
    metric.samples = samples
    return metric
