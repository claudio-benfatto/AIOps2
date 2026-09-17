# MetaSRE — 60-Hour Scoped Plan

## The one claim this version must prove

> Given an incident in a small AI system, and access only to its telemetry and
> operational APIs, MetaSRE produces a root-cause analysis with cited evidence,
> and we can measure how often it is right, how long it takes and what it costs.

Everything in scope serves that claim. Everything else is in "Later".

## Key scoping decisions

**1. Simulate the inference layer instead of running vLLM.**
A GPU-free `llm-sim` service replaces vLLM for the target system. It models
queueing, prefill cost (proportional to input tokens), decode cost, and a
finite KV-cache budget. It exposes vLLM-style metrics (TTFT, TPOT, waiting
requests, KV-cache usage). This makes faults deterministic, the benchmark
reproducible, and the whole lab free to run. The simulator's credibility comes
from modelling the mechanisms honestly, and the write-up should say so plainly.

To keep the door open to plugging in a real vLLM (or any OpenAI-compatible
backend) later without touching `agent-svc`, dashboards or investigator
queries:
- `llm-sim` exposes `POST /v1/chat/completions` with OpenAI's request/response
  schema (`messages`, `tools`, `tool_calls`, `model`, `usage`). The
  deterministic tool-call policy fills in an OpenAI-shaped response, not a
  bespoke schema.
- `agent-svc` reads the backend base URL from config/env (e.g. `LLM_BASE_URL`)
  and forwards an `Authorization` header if configured; it never hardcodes
  `llm-sim`-specific assumptions beyond the OpenAI schema.
- The public `/metrics` endpoint emits literal `vllm:`-prefixed series for
  every mechanism with a real equivalent (`vllm:time_to_first_token_seconds`,
  `vllm:time_per_output_token_seconds`, `vllm:num_requests_waiting`,
  `vllm:num_requests_running`, `vllm:gpu_cache_usage_perc`,
  `vllm:prompt_tokens_total`, `vllm:generation_tokens_total`), so Grafana
  panels and PromQL used by the investigator work unmodified against a real
  vLLM later. No sim-only metric may leak fault state (invariant 1 still
  applies).
- The fault-control endpoint stays `llm-sim`-only, on its separate internal
  port, never part of the shared API surface. S2 (`kv_pressure`) and S4
  (`model_regression`) depend on it and are therefore sim-only scenarios —
  a documented limitation, not a blocker.
- Streaming (`stream: true`, SSE) is a stretch item for later fidelity, not
  required for M1's budget.

**2. The target agent's "LLM" is scripted; the investigator's LLM is real.**
The target agent calls `llm-sim`, which returns tool-call decisions from a
deterministic policy (retrieve → search → answer; retry on tool error; etc.).
Cascades such as *search latency → retries → more steps → larger context →
higher TTFT* then emerge from the mechanics rather than being hard-coded.
Only the MetaSRE investigator uses a real LLM API.

**3. One all-in-one observability backend.**
Use the `grafana/otel-lgtm` image (OTel Collector + Prometheus + Loki + Tempo +
Grafana) as a single deployment. Wiring those up separately is a day of work
that proves nothing new.

**4. kind + plain manifests (Kustomize), no Helm/Argo CD.**
Kubernetes is kept because rollouts, restarts and events are part of the
evidence the investigator uses. GitOps tooling adds no value to the claim.

**5. Hand-rolled investigation loop, no LangGraph.**
A plain tool-use loop with an explicit hypothesis ledger is faster to build,
easier to debug, and shows the reasoning design more clearly in a portfolio.

**6. Read-only and advisory.**
The investigator recommends remediation but never executes it.

**7. No fabricated baselines.**
The original doc's human-vs-MetaSRE table is dropped. Only measured numbers go
in the results.

**8. `load_gen` and the lab fault-injector CLI are written in Go.**
Both are isolated from the Pydantic-heavy core (RCA schema, scenario ground
truth, scoring) and don't need to change if the language differs from the
rest of the stack:
- `load_gen` is a concurrent traffic generator — an idiomatic Go use case
  (goroutines/channels for a bounded worker pool, `context` for cancellation,
  `time.Ticker` for rate limiting), and this version is meant to showcase
  those primitives rather than just port a Python script.
- `lab/injector` (the `metasre-lab inject/clear/reset` CLI) is a classic
  single-binary Go CLI: it calls fault-control endpoints and drives `kubectl`
  rollouts. It reads only the injection-steps subset of `scenarios/*.yaml`;
  the scenario loader, benchmark runner and scoring (which need the full spec
  incl. ground truth, tied to the RCA Pydantic models) stay Python. This is a
  deliberate, small duplication of the YAML injection-steps shape across two
  languages — acceptable because that subset is tiny and stable (fault type,
  target component, params, duration).

Cost: two extra toolchains (Go compiler, `golangci-lint`) and two extra
Dockerfiles/build steps in `make build`; `make lint`/`test`/`typecheck` must
run both toolchains. Everything else (investigator, agent-svc, llm-sim,
scoring, benchmark harness) stays Python — this is not a general polyglot
push.

**9. Investigator self-critique loop, human-reviewed refinement.**
Before `submit_rca`, the investigator runs one bounded critic pass over its
own draft RCA: a second LLM call checks evidence sufficiency, internal
consistency and confidence calibration — without access to ground truth,
so this is realistic to how a real investigator would self-check (no oracle
in production either). The investigator may revise once based on the
critique, within the existing tool/token/time budgets (no separate unbounded
budget for the critique-and-revise cycle, so cost and wall-clock time per run
stay comparable across benchmark runs). The critique score/text is attached
to the RCA output and exposed as investigator OTel logs/metrics (extending
the M4 self-instrumentation), so it's visible in Grafana alongside the target
system's telemetry.

"Continuous refinement" is a human workflow, not an automated one: after
benchmark runs, a person reads the aggregated critique scores in
`results/*.jsonl` and decides whether to edit the investigator's prompt or
hypothesis-ledger rules, committed as an ordinary code change. This keeps
every benchmark number attributable to a specific, versioned investigator
(invariant 6) and deliberately stops short of "autonomous operation"
(explicitly out of scope, see Later). This decision absorbs and supersedes
the Stretch item "LLM-as-judge scoring of the causal chain" — it's now core,
not stretch.

Cost: ~+4h (M3 +3h for the critic call, revise loop and RCA schema field;
M4 +1h for capturing the critique score per run and extending
self-instrumentation). Total budget moves from 60h to ~64h to absorb this
rather than cutting other scope.

## Target system

```
load-gen ──► agent-svc ──► llm-sim        (vLLM-like metrics, KV budget)
                 │
                 ├──► retrieval-svc       (pgvector or in-memory)
                 └──► search-api          (fake external dependency)

load-gen is Go; agent-svc, llm-sim, retrieval-svc, search-api are Python.
All services: OpenTelemetry traces/metrics/logs ──► otel-lgtm
```

Each service exposes an internal fault-control endpoint used only by the
fault injector. Fault state is never exported as telemetry.

## Incident scenarios (5 + control)

| ID | Injection | Mechanism the investigator must uncover | Change event? |
|----|-----------|-----------------------------------------|---------------|
| S1 `search_latency` | runtime | search slow → timeouts → agent retries → more steps → context growth → TTFT up | no |
| S2 `kv_pressure` | runtime | KV budget reduced (noisy neighbour) → queueing/preemption → TTFT up, throughput down | no |
| S3 `agent_loop` | rollout (ConfigMap) | bad agent config → repeated tool calls → steps and tokens explode | yes |
| S4 `model_regression` | rollout (llm-sim model version) | new version emits invalid structured output → parse failures → retries | yes |
| S5 `retrieval_oom` | rollout (memory limit) + leak | retrieval pod OOMKilled/restarting → tool errors → degraded answers | yes |
| S0 `control` | none | nothing is wrong; investigator should say so | no |

S1 is the flagship scenario. Build it end to end before the others.

The RCA taxonomy offered to the investigator is deliberately wider than these
five (roughly 12 categories), so the answer space doesn't give the game away.

## Milestones

Total: 57h planned + 7h buffer = 64h.
Each milestone ends in something demoable.

### M0: Foundation (5h)
1. Repo skeleton (uv workspace, ruff, pytest, Makefile) plus two Go modules
  (`services/load_gen`, `lab/injector`) with `gofmt`/`go vet`/`golangci-lint`/
  `go test` wired into `make lint`/`test`/`typecheck`
2. kind cluster + otel-lgtm deployed via Kustomize
3. `topology.yaml`: static operational graph (components, edges, ids)
4. ADRs for decisions 1–6, 8 and 9 above

**Deliverable:** `make up` gives a running cluster with Grafana reachable.

### M1: Observable target system (13h)
1. `llm-sim` with the latency/KV model and vLLM-style metrics; HTTP surface
  (`/v1/chat/completions`) and metric names are OpenAI/vLLM-compatible by
  construction (see decision #1) — don't invent a custom schema
2. `agent-svc` with step loop, retries, max-steps guard
3. `search-api`, `retrieval-svc`
4. `load-gen` (Go): bounded worker pool over goroutines/channels, `context`-based
  cancellation, `time.Ticker` rate limiting, OTel Go SDK for traces/metrics
5. OTel instrumentation using GenAI semantic conventions where applicable
6. Grafana dashboard: latency, TTFT, tokens, agent steps, tool calls/errors, KV usage

**Deliverable:** a dashboard screenshot and a trace showing
agent → tools → LLM spans with token attributes.
*This is already a publishable mini-piece ("instrumenting an AI agent").*

### M2: Incident lab (7h)
1. Fault-control endpoints + `metasre-lab inject/clear/reset` CLI (Go,
  `lab/injector`), reading the injection-steps subset of the scenario spec
2. Scenario specs in `scenarios/*.yaml` (injection, ground truth, expected
  symptoms) — Python-side scenario loader (used by scoring) keeps the full spec
3. A symptom check per scenario confirming the fault is visible in telemetry

**Deliverable:** `make inject SCENARIO=S1` produces a visible, repeatable
incident; scenario catalogue in docs.

### M3: Investigator v1 (16h)
1. Read-only tools: PromQL, LogQL, Tempo search/trace fetch, K8s events,
  rollout history, topology lookup
2. Hypothesis ledger tools: `propose`, `add_evidence`, `reject`
3. `submit_rca` with a Pydantic schema: symptom, hypotheses (accepted/rejected
  with evidence), root cause (component id + category), causal chain,
  confidence, recommended remediation, self-review (critique text + score)
4. Self-critique pass before `submit_rca`: one bounded critic call reviews the
  draft RCA for evidence sufficiency/consistency (no ground truth); the
  investigator may revise once, within the existing budgets (see decision #9)
5. Budgets: max tool calls, max tokens, wall-clock timeout (cover the
  critique-and-revise cycle, not a separate budget)
6. Markdown RCA renderer (includes the self-review section)

**Deliverable:** a correct, evidence-backed RCA for S1, committed as an example
report, including its self-review. *Record a short demo here.*

### M4: Benchmark harness (9h)
1. Runner: reset → warm-up baseline → inject → wait → trigger investigation with
  an alert-style symptom only → score → clear
2. Deterministic scoring (component + category match; partial credit for
  component only) and false-positive check on S0
3. Metrics per run: correctness, time to RCA, tool calls, hypotheses,
  tokens, cost, stated confidence, self-review score
4. N=3 runs per scenario; results written to `results/*.jsonl` + summary table
5. Investigator instrumented with OTel (its own token cost, latency and
  self-review score/logs appear in Grafana: the small, cheap "meta" nod)

**Deliverable:** `make bench` produces a results table across all scenarios.

### M5: Context ablation and publication (7h)
1. Ablation: metrics-only vs metrics+logs vs metrics+logs+traces vs
  full (+K8s + topology). This is one of the original research questions and
  is nearly free once the harness exists.
2. README with architecture diagram, quickstart, results, limitations
3. Write-up / blog post and a 2–3 minute demo video

**Deliverable:** a public repo and a write-up with measured results.

### Buffer (7h)
Reserved for the things that always slip: OTel wiring, kind networking,
and investigator prompt iteration.

## Cut lines (if running behind, drop in this order)

1. The demo video (keep GIFs/screenshots)
2. Ablation reduced to two arms (metrics-only vs full)
3. S5 (`retrieval_oom`)
4. N=3 reduced to N=1
5. S2 (`kv_pressure`)

Never cut: S1, S0, the scoring harness, the RCA schema with evidence.

## Stretch (only if the buffer is unused)

1. Alert-driven trigger: poll Prometheus alerts and start investigations
2. One **controlled experiment** for S2: temporarily change `llm-sim` KV/context
  config, measure TTFT, update confidence (a preview of original Milestone 5)
3. A red-herring scenario: a harmless rollout happening during S1

## Later (explicitly out of scope for the 60h)

Real vLLM/GPUs, KServe, KubeRay, Temporal, OPA, remediation execution,
approval workflows, autonomous operation, MetaSRE operating itself as a target,
Kafka-based change/event bus, AWS deployment.