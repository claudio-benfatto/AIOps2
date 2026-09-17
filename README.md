# AIOps2

AIOps2 is an AI investigator that diagnoses incidents in another AI system.
The repo contains three things:

1. **Target system:** a small, deliberately faultable AI application
   (agent + simulated LLM server + tools) running on kind.
2. **Incident lab:** fault injection and scenarios with hidden ground truth.
3. **Investigator:** an LLM agent that reads telemetry and produces an
   evidence-backed RCA. It is benchmarked against the lab.

The goal is to show one claim with measured results: *given only telemetry
and operational APIs, the investigator identifies the root cause and cites
evidence.* See [`docs/PLAN.md`](docs/PLAN.md) for the full scope, milestones
and hour budget.

## Prerequisites

`make up` needs a local container runtime plus `kind` and `kubectl`:

- A running container runtime: [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/)
  or `brew install colima docker && colima start`.
- `brew install kind kubectl`

`make up` checks for these and fails with an install hint if any are missing.

## Structure

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
scenarios/          # S0-S5 YAML specs, incl. ground truth
deploy/             # Kustomize bases/overlays, kind config, dashboards
topology.yaml       # operational graph: component ids and dependency edges
results/            # benchmark outputs (jsonl + summaries)
docs/               # PLAN.md, ADRs (docs/adr/NNNN-title.md), scenario catalogue, write-up
```

More detail to follow as each milestone lands.
