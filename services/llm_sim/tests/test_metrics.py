from __future__ import annotations

from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client.parser import text_string_to_metric_families

from llm_sim.metrics import SimulationCollector
from llm_sim.state import SimulationState

EXPECTED_METRIC_TYPES = {
    "vllm:num_requests_running": "gauge",
    "vllm:num_requests_waiting": "gauge",
    "vllm:kv_cache_usage_perc": "gauge",
    "vllm:prompt_tokens_total": "counter",
    "vllm:generation_tokens_total": "counter",
    "vllm:time_to_first_token_seconds": "histogram",
    "vllm:inter_token_latency_seconds": "histogram",
    "vllm:e2e_request_latency_seconds": "histogram",
}


def test_exposed_metrics_match_readme_table_exactly() -> None:
    """Parses the actual `/metrics` wire format (what generate_latest()
    renders), not just the pre-render `Metric.name` from `collect()` —
    those can legitimately differ for counters (see metrics.py's
    `_counter` docstring). `text_string_to_metric_families` itself
    re-canonicalizes a counter family's `.name` back to the bare,
    un-suffixed form (its own data model always treats "_total" as a
    render-time decoration), so the literal exposed series name for a
    counter has to be read off its sample instead of the family object —
    that sample name is what Prometheus and the investigator's PromQL
    queries actually scrape."""
    registry = CollectorRegistry()
    registry.register(SimulationCollector(SimulationState(kv_cache_budget_tokens=1000)))
    text = generate_latest(registry).decode()

    families: dict[str, str] = {}
    for family in text_string_to_metric_families(text):
        if family.type == "counter":
            name = next(s.name for s in family.samples if s.name.endswith("_total"))
        else:
            name = family.name
        families[name] = family.type

    assert families == EXPECTED_METRIC_TYPES
