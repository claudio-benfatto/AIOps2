# CLAUDE.md — AIOps2

## What this project is

AIOps2 is an AI investigator that diagnoses incidents in another AI system.
The repo contains three things:

1. **Target system:** a small, deliberately faultable AI application
   (agent + simulated LLM server + tools) running on kind.
2. **Incident lab:** fault injection and scenarios with hidden ground truth.
3. **Investigator:** an LLM agent that reads telemetry and produces an
   evidence-backed RCA. It is benchmarked against the lab.

The goal of this version is to show one claim with measured results: *given
only telemetry and operational APIs, the investigator identifies the root
cause and cites evidence.* The scope, milestones and hour budget are in
`docs/PLAN.md`. Read it before starting any milestone work.

## Current status

<!-- Update this block at the end of every working session. -->
- Current milestone: M0
- Done: —
- Next: —
- Hours spent so far: 0 / 64

## Architecture

```
load-gen ──► agent-svc ──► llm-sim
                 ├──► retrieval-svc
                 └──► search-api
all ──OTel──► otel-lgtm (Collector, Prometheus, Loki, Tempo, Grafana)

investigator ──read-only tools──► Prometheus / Loki / Tempo / K8s API / topology.yaml
investigator ──OTel (own tokens, latency, self-review score/logs)──► otel-lgtm
lab (injector, bench) ──► fault-control endpoints, kubectl rollouts
```

## Repository layout

```
services/
  llm_sim/          # GPU-free inference simulator (queue, prefill, decode, KV budget)
  agent_svc/        # target agent: step loop, tool calls, retries
  search_api/       # fake external dependency
  retrieval_svc/    # vector retrieval
  load_gen/         # traffic generator (Go, own go.mod)
  common/           # shared OTel setup, fault-control router, config
investigator/       # AIOps2: loop, tools, hypothesis ledger, RCA schema, renderer
lab/
  injector/         # fault injector CLI (Go, own go.mod): calls fault-control
                     # endpoints, drives kubectl rollouts
  ...                # scenario loader, benchmark runner, scoring (Python)
scenarios/          # S0–S5 YAML specs, incl. ground truth
deploy/             # Kustomize bases/overlays, kind config, dashboards
topology.yaml       # operational graph: component ids and dependency edges
results/            # benchmark outputs (jsonl + summaries)
docs/               # PLAN.md, ADRs (docs/adr/NNNN-title.md), scenario catalogue, write-up
```

## Tech stack

Python 3.12, uv (workspace), FastAPI, httpx, Pydantic v2, OpenTelemetry SDK,
Anthropic Python SDK (investigator only), pytest, ruff, mypy (strict for
`investigator/` and the Python parts of `lab/`). Infra: kind, Kustomize,
`grafana/otel-lgtm`.

`services/load_gen/` and `lab/injector/` are Go (see PLAN.md scoping decision
on polyglot components) — each its own `go.mod`, no shared Go code between
them yet. Go tooling: `gofmt`, `go vet`, `golangci-lint`, `go test`,
OpenTelemetry Go SDK for traces/metrics. `make lint`/`make test`/`make
typecheck` must cover both toolchains.

Investigator model is set by `INVESTIGATOR_MODEL` (default `claude-sonnet-5`);
the API key comes from `ANTHROPIC_API_KEY`. Never hard-code either.

## Commands

```
make up                 # create kind cluster, deploy observability + target system
make down               # delete cluster
make build              # build and load images into kind
make load               # start load generator
make inject SCENARIO=S1 # inject a scenario's fault
make clear              # clear all faults and roll back scenario rollouts
make investigate        # run investigator against current state with an alert symptom
make bench              # full benchmark (all scenarios × N runs)
make test / make lint / make typecheck
```

If a command you need doesn't exist yet, add it to the Makefile rather than
documenting a long ad-hoc command.

## Invariants (do not break these)

1. **Fault state is hidden from the investigator.**
   - Never export fault flags, scenario ids or injection details as metric
     labels, span attributes or log fields.
   - Faults must show up only through their *effects* (latency, errors,
     retries, restarts, rollouts).
   - The investigator has no tool that can reach fault-control endpoints,
     `scenarios/`, `lab/` state or the source tree.
   - Fault-control endpoints listen on a separate internal port that is not
     scraped.
2. **Fault code paths are intentional.** Code in `services/` that makes things
   slow, loop, fail or leak exists on purpose. Don't "fix" it, and don't add
   defensive handling that masks a scenario's symptoms. Put such code behind
   the fault-control router and mark it with `# FAULT:` comments.
3. **The investigator is read-only.** Its tools may only issue GET/query calls.
   Remediation is a recommendation in the RCA and is never executed.
4. **Cascades must emerge from mechanics.** For example, S1's retries and
   context growth come from real agent retry logic and prompt accumulation,
   not from a fault that directly raises TTFT.
5. **llm-sim is deterministic under a seed.** All randomness goes through a
   seeded RNG so benchmark runs are reproducible.
6. **Every benchmark number is measured.** No placeholder or illustrative
   results in `results/`, README or docs.
7. **The RCA must cite evidence.** Every accepted or rejected hypothesis
   references at least one tool result (query + observed value).
8. **Self-critique is bounded and non-autonomous.** The investigator's
   self-review pass (before `submit_rca`) may trigger at most one revision,
   within the same tool/token/time budgets as the rest of the run — no
   separate or unbounded budget for it. Refinement based on self-review
   scores (prompt/ledger-rule changes) is a human workflow done between runs,
   never automated within or across runs. See PLAN.md decision #9.

## Conventions

- Type hints everywhere; Pydantic models for all API payloads, scenario specs
  and the RCA schema.
- Follow OpenTelemetry GenAI semantic conventions (`gen_ai.*`) for LLM spans
  where applicable. Mirror vLLM metric naming in `llm-sim` where practical, and
  document the mapping in `services/llm_sim/README.md`.
- Component ids in telemetry (`service.name`) must match ids in
  `topology.yaml`. Scoring relies on this.
- Keep the RCA category taxonomy in one place (`investigator/taxonomy.py`).
  It must stay wider than the set of scenarios.
- Tests: unit tests for the llm-sim latency model, scoring and RCA schema;
  a smoke test per scenario that checks the symptom appears in telemetry.
  Don't write tests that require the real LLM API; use recorded or fake
  responses.
- Logs are structured JSON with trace/span ids.
- Record significant design decisions as ADRs in `docs/adr/`.
- Go components (`load_gen`, `lab/injector`): idiomatic concurrency
  (goroutines/channels/context), no third-party framework beyond the
  OpenTelemetry Go SDK and a YAML lib for reading `scenarios/*.yaml`; errors
  wrapped with `%w`; table-driven tests. `lab/injector` reads only the
  injection-steps subset of a scenario spec — it does not duplicate the
  ground-truth/scoring model that stays in the Python side of `lab/`.

## Adding a scenario

1. Implement the fault behind the fault-control router (or as a Kustomize
   overlay if it's a rollout-based fault).
2. Add `scenarios/SX_name.yaml` with injection steps, ground truth
   (`component`, `category`, causal chain) and expected symptoms.
3. Add a symptom smoke test.
4. Update the scenario catalogue in `docs/`.

## Adding an investigator tool

1. Implement it in `investigator/tools/` as a read-only function with a
   Pydantic input model and a size-bounded output (truncate or summarise
   large results; report that truncation happened).
2. Register it with a clear description aimed at the model.
3. Make sure it respects the ablation flags (`--context metrics|logs|traces|full`).
4. Add a unit test with a fake backend.

## How to work in this repo

- Stay within the current milestone in `docs/PLAN.md`. If something from a
  later milestone or the "Later" list looks necessary, stop and ask first.
- Before adding a dependency or a new infrastructure component, ask.
- Prefer small, reviewable changes and run `make lint test` before
  declaring a task done.
- When a milestone deliverable is reached, update the status block above and
  note the hours spent.
- If a task looks likely to exceed its milestone's hour budget, say so early
  and propose what to cut, using the cut lines in `docs/PLAN.md`.