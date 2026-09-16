---
name: python
description: Python conventions for AIOps2 — uv workspace, src layout, strict typing scope, ruff, pytest. Use whenever adding a Python package, module, dependency, or test in this repo.
---

# AIOps2 Python conventions

Applies to `services/agent_svc`, `services/llm_sim`, `services/search_api`,
`services/retrieval_svc`, `services/common`, `investigator/`, and the Python
parts of `lab/`. Python 3.12. Does not apply to `services/load_gen` or
`lab/injector` (Go — see the `go` skill).

## Project structure

- One `uv` workspace at the repo root (root `pyproject.toml` with
  `[tool.uv.workspace] members = [...]`); each service/package under
  `services/*` and `investigator/` is its own workspace member with its own
  `pyproject.toml`.
- `src/` layout per member (`services/llm_sim/src/llm_sim/...`), so imports
  can't accidentally resolve against the working directory instead of the
  installed package.
- Shared OTel setup, fault-control router, and config helpers live in
  `services/common` and are a workspace dependency of the other services —
  don't duplicate them.
- Run everything through `uv run ...` / `uv sync`; don't hand-edit lockfiles.

## Typing

- Type hints everywhere, including internal helpers and test fixtures.
- Pydantic v2 (`BaseModel`, not v1-style `class Config`) for every API
  payload, scenario spec, and the RCA schema — use `model_config =
  ConfigDict(...)` and `field_validator`, not deprecated v1 validators.
- `mypy --strict` is required for `investigator/` and the Python parts of
  `lab/` (CLAUDE.md tech stack). Services under `services/` should still be
  fully typed but aren't held to `--strict` unless the milestone says
  otherwise — check `pyproject.toml`'s `[tool.mypy]` overrides before
  assuming which mode applies to a given member.
- Prefer precise types over `Any`; if a third-party stub is missing, add a
  narrow local stub or a targeted `# type: ignore[code]` with the reason,
  not a blanket ignore.

## Style & tooling

- `ruff` for both linting and formatting (`ruff format`, `ruff check`) —
  no black/isort/flake8. Config lives in the root `pyproject.toml`
  (`[tool.ruff]`) so all members share one rule set unless a member has a
  documented reason to diverge.
- No comments that restate what the code does; only comment a non-obvious
  *why* (a workaround, a fault-injection hook, a subtle invariant).
- Structured JSON logs with trace/span ids (CLAUDE.md conventions) — use the
  shared logging setup in `services/common`, don't roll a new one per
  service.
- Follow OpenTelemetry GenAI semantic conventions (`gen_ai.*`) for LLM spans.

## Tests

- `pytest`, colocated as `tests/` per workspace member.
- Unit tests required for: the llm-sim latency/KV model, scoring, and the
  RCA schema (validation edge cases, not just the happy path).
- One symptom smoke test per scenario, asserting the fault is visible in
  telemetry — not asserting on fault-control state (invariant 1: fault
  state must stay invisible to anything the investigator can reach).
- Never write a test that calls the real Anthropic API. Use recorded
  responses (fixtures) or a fake/deterministic backend. If you're adding a
  new investigator behavior, record the fixture once and check it in next
  to the test rather than re-recording on every run.
- Table-style parametrization (`@pytest.mark.parametrize`) over copy-pasted
  near-duplicate test functions.

## Dependencies

- Ask before adding a new third-party dependency (CLAUDE.md: "Before adding
  a dependency ... ask"). Prefer the standard library or an existing
  workspace dependency first.
- Pin via `uv.lock`; don't add version ranges speculatively.

## Before committing

`make lint test typecheck` must pass locally. These wrap `ruff check`,
`ruff format --check`, `pytest`, and `mypy` for every workspace member — if
the command you need isn't in the Makefile yet, add it there rather than
running ad-hoc `uv run` commands that CI won't reproduce.
