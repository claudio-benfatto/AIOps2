# llm-sim

GPU-free inference simulator standing in for vLLM (`docs/adr/0001`). Models
queueing, prefill/decode cost, and a finite KV-cache budget, and exposes
`vllm:`-prefixed Prometheus metrics so Grafana dashboards and investigator
PromQL work unmodified against a real vLLM backend later.

## vLLM metric mapping

Selection criteria and update process: `docs/adr/0009`.

Pinned to: vLLM stable docs (`docs.vllm.ai/en/stable`), retrieved
2026-09-17. No installed vLLM version was available to confirm an exact
release number — confirm against `vllm.__version__` if one is ever
installed alongside this repo, and update this pin deliberately rather than
silently.

| llm-sim metric | Type | vLLM mechanism modeled |
|---|---|---|
| `vllm:num_requests_running` | gauge | requests in the active execution batch |
| `vllm:num_requests_waiting` | gauge | queue depth |
| `vllm:kv_cache_usage_perc` | gauge | KV-cache budget pressure |
| `vllm:prompt_tokens_total` | counter | prefill tokens processed |
| `vllm:generation_tokens_total` | counter | decode tokens processed |
| `vllm:time_to_first_token_seconds` | histogram | queueing + prefill latency (TTFT) |
| `vllm:inter_token_latency_seconds` | histogram | per-token decode latency (ITL) |
| `vllm:e2e_request_latency_seconds` | histogram | full request latency |

This table covers the M1.6 dashboard's named needs (latency, TTFT, tokens,
KV usage) plus the metrics required to compute them; it is not a copy of
vLLM's full metrics surface (LoRA, spec-decoding, prefix-cache, multimodal
cache, KV-connector stats, etc. have no modeled equivalent here and are
intentionally left out per ADR 0009).

Two corrections vs. ADR 0001's original wording, found when this table was
pinned: `gpu_cache_usage_perc` is now `kv_cache_usage_perc`, and
`time_per_output_token_seconds` is superseded by
`inter_token_latency_seconds` in vLLM's v1 engine. ADR 0001 itself is left
unedited (ADRs are a historical record, not a living doc); this table is
the current source of truth.

No metrics are implemented yet — this table is the spec for the rest of
M1.1's build (latency/KV model, HTTP surface, Prometheus exporter). Every
metric must be read off a single simulation-state object that only the
queue/prefill/decode/KV mechanics update — the exporter never writes a
metric value directly (`docs/adr/0009`). Once that code lands, add two
kinds of tests: a contract test asserting the exposed metric names/types
match this table exactly, and a behavioral test per mechanism asserting its
metric actually moves when the mechanism is driven (e.g. more concurrent
requests raises `vllm:num_requests_waiting`) — the first catches naming
drift, the second catches a metric that exists but is disconnected from the
model.
