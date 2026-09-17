# 0005. Hand-rolled investigation loop, no LangGraph

## Status
Accepted

## Context
The investigator's core contribution is a tool-use loop with an explicit
hypothesis ledger (propose/add_evidence/reject) that produces an
evidence-backed RCA. That reasoning design is the thing this project needs to
demonstrate clearly, both to build and to explain in a portfolio write-up.

## Decision
Implement the investigation loop directly (a plain tool-use loop plus a
hypothesis ledger) rather than adopting a graph/orchestration framework like
LangGraph.

## Consequences
- Faster to build and easier to debug than learning and fitting the problem
  into a framework's abstractions.
- The reasoning design (ledger states, tool budgets, self-critique pass) is
  fully visible in `investigator/` rather than partly hidden behind
  framework internals.
- No framework-provided features (built-in checkpointing, visual graph
  debugging) — acceptable at this project's scale and budget.
