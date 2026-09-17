# 0001. Simulate the inference layer instead of running vLLM

## Status
Accepted

## Context
Running real vLLM would require GPUs, making the lab expensive and the
benchmark non-reproducible. The investigator still needs realistic,
fault-injectable inference metrics (TTFT, TPOT, KV-cache pressure) to
diagnose against.

## Decision
Replace vLLM with `llm-sim`, a GPU-free service that models queueing,
prefill/decode cost, and a finite KV-cache budget, and exposes literal
`vllm:`-prefixed metrics plus an OpenAI-compatible `/v1/chat/completions`
surface so a real backend could be swapped in later without touching
`agent-svc`, dashboards, or investigator queries.

## Consequences
- Faults are deterministic and the benchmark is reproducible and free to run.
- S2 (`kv_pressure`) and S4 (`model_regression`) depend on sim-only
  fault-control and are therefore sim-only scenarios — a documented
  limitation, not a blocker.
- Streaming (SSE) is deferred as a stretch item, not required for M1.
- The simulator's credibility rests on modelling mechanisms honestly; the
  write-up must say so plainly.
