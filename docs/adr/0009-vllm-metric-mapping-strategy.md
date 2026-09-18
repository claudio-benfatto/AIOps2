# 0009. vLLM metric selection and maintenance strategy

## Status
Accepted

## Context
ADR 0001 commits `llm-sim` to exposing literal `vllm:`-prefixed metric
names so Grafana panels and investigator PromQL work unmodified against a
real vLLM backend later. But "mirror vLLM" isn't a stable target on its
own: vLLM renames and deprecates metrics between versions (it ships a
`show_hidden_metrics_for_version` config specifically for this), and
ADR 0001's own example names have already drifted from current vLLM
(`gpu_cache_usage_perc` is now `kv_cache_usage_perc`;
`time_per_output_token_seconds` is superseded by
`inter_token_latency_seconds`). Without a defined selection scope and
review process, the mapping degrades silently over the life of the
project, undermining the "vLLM-compatible by construction" claim M1.1 and
the write-up depend on.

## Decision
Select llm-sim metrics by three criteria: (1) the name/type mirrors a real
vLLM metric 1:1 — no invented schema; (2) llm-sim actually models the
mechanism behind it — no metric without backing logic in the
queue/prefill/decode/KV model; (3) it's needed by something already named
in PLAN.md (the M1.6 dashboard or an M3 investigator tool), not vLLM's full
metrics surface. Pin the mapping to a specific vLLM docs snapshot recorded
in `services/llm_sim/README.md`, and treat re-checking that pin as a
deliberate, human-reviewed step — before M5 (publication) and whenever
someone chooses to bump it — rather than automated tracking of upstream
vLLM.

Enforce criterion (2) two ways rather than by review discipline alone:
structurally, every metric is read off a single simulation-state object
that only the queue/prefill/decode/KV mechanics update — the exporter has
no path to write a metric value directly, so an unbacked metric has nowhere
to get its value from; and behaviorally, each mechanism's unit test drives
the model and asserts the metric moves in response (e.g. more concurrent
requests raises `vllm:num_requests_waiting`), not just that its name/type
matches the README table — the README-table contract test only catches
naming drift, not a metric that exists but is disconnected from the model.

## Consequences
- Most of vLLM's metrics surface (LoRA, spec-decoding, prefix-cache,
  multimodal cache, KV-connector stats, etc.) never appears in llm-sim —
  intentional, since none of it has a modeled mechanism or a named
  consumer.
- The mapping can still silently drift from real vLLM between review
  points; a future contract test (added once M1.1's metrics code exists)
  only catches llm-sim disagreeing with its own documented table, not
  llm-sim disagreeing with upstream vLLM.
- `services/llm_sim/README.md` becomes the living source of truth for the
  current metric set and vLLM version pin; it's edited directly in
  ordinary PRs as llm-sim grows, not through further ADRs.
- No new infrastructure (e.g. CI scraping vLLM's docs) is introduced,
  consistent with the project's existing preference for human-reviewed
  refinement over automation (ADR 0008).
- The single-state-object shape constrains how llm-sim's internals are
  structured, not just its exporter — mechanics must write to shared state
  rather than computing a metric value inline, which is a real design
  constraint on the rest of M1.1's implementation.
- Enforcement still relies on code review and test coverage, not a static
  gate; a metric wired to state that the mechanics update only cosmetically
  (e.g. copied but never driven by real load) would still pass both checks.
