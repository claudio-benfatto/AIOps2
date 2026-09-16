---
name: git-workflow
description: Conventional Commits and PR conventions for AIOps2 — commit types, module-mapped scopes, and the PR body template. Use whenever drafting a commit message or opening a PR in this repo.
---

# AIOps2 git workflow

## Commit message format

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

- Subject: imperative mood, no trailing period, ≤72 chars (e.g. `add KV budget model to llm-sim`, not `Added...` or `adds...`).
- Body (optional): the *why*, not a restatement of the diff — wrap at ~100 cols.
- Breaking changes: add a `BREAKING CHANGE:` footer, or append `!` after the scope (`feat(investigator)!: ...`). This repo has no external consumers yet, so use this only for changes to the RCA schema, scenario spec format, or tool contracts that would break saved results/recordings.
- Reference issues/ADRs in the footer when relevant: `Refs: docs/adr/0004-....md`.

commitlint (`@commitlint/config-conventional`) enforces type, scope-is-lowercase, and subject rules on every commit — see the `commit-msg` hook in `.pre-commit-config.yaml`.

## Types

| Type | Use for |
|---|---|
| `feat` | new capability (a new tool, scenario, endpoint, metric) |
| `fix` | bug fix, including fault-injection bugs and scoring bugs |
| `docs` | `docs/`, README, ADRs, this skill, CLAUDE.md/PLAN.md updates |
| `style` | formatting only (ruff format, gofmt) — no logic change |
| `refactor` | restructuring with no behavior change |
| `perf` | latency/throughput/cost improvement with no behavior change |
| `test` | adding or fixing tests only |
| `build` | dependencies, Dockerfiles, `pyproject.toml`, `go.mod`, Kustomize bases |
| `ci` | `.github/workflows/`, pre-commit config, release-please config |
| `chore` | everything else that isn't user- or reader-facing (repo hygiene) |
| `revert` | reverting a prior commit — use git's own `revert` subject format |

## Scopes

Scope = the module you touched, matching `services/`, `investigator/`, `lab/`, etc. in CLAUDE.md's repository layout. Keep it to one scope per commit; if a change spans several, either it's `chore`/`refactor` with no scope, or it should be split into smaller commits.

| Scope | Maps to |
|---|---|
| `llm-sim` | `services/llm_sim/` |
| `agent-svc` | `services/agent_svc/` |
| `search-api` | `services/search_api/` |
| `retrieval-svc` | `services/retrieval_svc/` |
| `common` | `services/common/` |
| `go/load-gen` | `services/load_gen/` (Go module) |
| `investigator` | `investigator/` |
| `go/injector` | `lab/injector/` (Go module) |
| `lab` | the Python parts of `lab/` (scenario loader, benchmark runner, scoring) |
| `scenarios` | `scenarios/*.yaml` |
| `deploy` | `deploy/` (Kustomize, kind config, dashboards) |
| `topology` | `topology.yaml` |
| `docs` | `docs/` |
| `repo` | root-level config (Makefile, CLAUDE.md, PLAN.md, `.claude/`, CI) |

No scope at all is fine for a change too broad for one (e.g. `chore: bump ruff across all pyproject.toml`).

Examples: `feat(llm-sim): model finite KV-cache budget`, `fix(go/injector): clear fault state on reset`, `test(investigator): cover ledger reject path`, `ci(repo): add golangci-lint job`.

## PR body template

```markdown
## What
<1-3 bullets: the change, in plain terms>

## Why
<the motivation — link the PLAN.md milestone, ADR, or scenario this serves>

## How tested
<commands run: `make lint test typecheck`, specific scenario/smoke test,
manual `make investigate` run, etc. Name what you did NOT test.>

## Risk
<blast radius: does this touch an invariant (docs/CLAUDE.md "Invariants"
section), fault-injection code, the RCA schema, or scoring? Anything that
needs a second look before merge?>
```

Keep "What" and "Why" separate even when they feel redundant — "What" is for someone skimming the diff, "Why" is for someone deciding whether the change belongs in this milestone's scope (see CLAUDE.md "How to work in this repo").

## Before opening a PR

- Run `make lint test typecheck` (covers both the Python and Go toolchains).
- If the change reaches a milestone deliverable, update the status block at the top of CLAUDE.md (current milestone, done/next, hours spent) in the same PR.
- If the change adds a scenario, confirm the four "Adding a scenario" steps in CLAUDE.md are all done (fault behind fault-control router, scenario YAML with ground truth, symptom smoke test, catalogue update).
