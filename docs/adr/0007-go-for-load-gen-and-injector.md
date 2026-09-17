# 0007. `load_gen` and the lab injector CLI written in Go

## Status
Accepted

## Context
`load_gen` (traffic generation) and `lab/injector` (the fault-injection CLI
that calls fault-control endpoints and drives `kubectl` rollouts) are both
isolated from the Pydantic-heavy core (RCA schema, scenario ground truth,
scoring) and don't share code with each other yet. `load_gen`'s concurrent
worker-pool shape and `lab/injector`'s single-binary CLI shape are both
idiomatic Go use cases, and showcasing those primitives has value beyond
just porting a Python script.

## Decision
Write `services/load_gen` and `lab/injector` in Go, each its own module with
its own `go.mod`. `lab/injector` reads only the injection-steps subset of a
scenario spec (fault type, target component, params, duration); the full
spec (ground truth, scoring) stays in the Python side of `lab/`. Everything
else in the system stays Python.

## Consequences
- Two extra toolchains (Go compiler, `golangci-lint`) and two extra
  Dockerfiles/build steps; `make lint`/`test`/`typecheck` must cover both
  languages.
- A small, deliberate duplication of the YAML injection-steps shape across
  Python and Go — accepted because that subset is tiny and stable.
- This is a scoped, two-component decision, not a general polyglot push:
  the investigator, agent-svc, llm-sim, scoring, and benchmark harness stay
  Python.
