---
name: go
description: Go conventions for AIOps2 — module layout, golangci-lint, table-driven tests, error wrapping, context propagation. Use whenever adding or editing code in services/load_gen or lab/injector.
---

# AIOps2 Go conventions

Applies only to `services/load_gen` (traffic generator) and `lab/injector`
(the `metasre-lab inject/clear/reset` CLI). These are two separate Go
modules — CLAUDE.md is explicit that there's no shared Go code between them
yet, so don't reach for a shared internal package across the two without
asking first (that would be a new inter-module dependency, i.e. new
infrastructure).

## Module layout

- Each of `services/load_gen` and `lab/injector` has its own `go.mod` — no
  workspace-wide `go.work` unless a later milestone asks for one.
- Standard layout per module: `main.go` (or `cmd/<name>/main.go` if the
  module grows a second binary), package-per-concern, `internal/` for
  anything not meant to be imported by the other module.
- No third-party framework beyond the OpenTelemetry Go SDK and a YAML
  library for reading `scenarios/*.yaml` (CLAUDE.md conventions) — check
  with the user before adding anything else (CLI frameworks, DI containers,
  etc.).
- `lab/injector` reads only the injection-steps subset of a scenario spec
  (fault type, target component, params, duration). It must not grow logic
  that duplicates the ground-truth/scoring model — that stays in the Python
  side of `lab/`.

## Concurrency

- `services/load_gen` is the showcase for idiomatic Go concurrency: a
  bounded worker pool over goroutines + channels, `context.Context` for
  cancellation (propagated from `main` down through every request), and
  `time.Ticker` for rate limiting. Don't reach for a job-queue library —
  this is meant to demonstrate the primitives directly.
- Every goroutine you spawn must have a clear shutdown path tied to context
  cancellation; no goroutine leaks on shutdown (verify with `-race` and, for
  load_gen, a short-lived integration run).
- `lab/injector` is mostly sequential (CLI calling fault-control endpoints
  and `kubectl`), but still thread a `context.Context` through for
  cancellation/timeouts on HTTP and subprocess calls.

## Errors

- Wrap with `%w`, always: `fmt.Errorf("inject fault for %s: %w", component, err)`.
- Don't swallow errors from `kubectl` subprocess calls or fault-control HTTP
  calls — surface stderr/response body in the wrapped error so a failed
  `make inject` is debuggable from the CLI output alone.
- Sentinel errors (`errors.Is` targets) only where a caller actually branches
  on the error kind; otherwise a wrapped error with context is enough.

## Style & tooling

- `gofmt` (or `gofumpt` if configured) on save — enforced by the
  `PostToolUse` hook, not something to run by hand.
- `go vet` and `golangci-lint` must be clean; see `.golangci.yml` at the repo
  root for the enabled linters (shared config for both modules unless one
  has a documented reason to diverge).
- Table-driven tests (`[]struct{ name string; ... }` + `t.Run(tt.name, ...)`)
  as the default test shape; avoid one-off test functions for cases that
  clearly belong in the same table.
- `go test -race` locally for anything touching goroutines (load_gen worker
  pool, any concurrent fault application in injector).

## Before committing

`make lint test typecheck` must cover both Go modules alongside the Python
side (CLAUDE.md: "`make lint`/`make test`/`make typecheck` must cover both
toolchains"). If a module-specific check doesn't have a Makefile target yet,
add one instead of running `go test ./...` ad hoc from inside the module
directory — CI must reproduce exactly what the Makefile runs.
