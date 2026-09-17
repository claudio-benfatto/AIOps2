---
name: adr
description: Architecture Decision Record structure and process for AIOps2 — five-part template, significance test, numbering/location. Use whenever recording a design decision or asked to write/update an ADR.
---

# AIOps2 ADRs

Applies to `docs/adr/`. An ADR captures one architecturally significant
decision — nothing more, nothing less.

## When to write one

Reserve an ADR for a choice that shapes structure, interfaces, or
dependencies and is costly to reverse. Skip reversible local details (a
helper's internal shape, a variable name, a config default that's a one-line
change to flip back). The test is significance, not difficulty — a decision
can be easy to make and still deserve a record if it's hard to undo.

## Structure

Five fixed parts, no more:

```markdown
# NNNN. Title

## Status
Accepted

## Context
<2-5 sentences: the forces and constraints that made this a decision, not
a restatement of the codebase>

## Decision
<2-4 sentences, imperative: what was decided>

## Consequences
- <short bullets: trade-offs, both what this buys and what it costs>
```

`Status` is one of `Proposed`, `Accepted`, `Deprecated`, or
`Superseded by NNNN`. Keep Context and Decision tight — an ADR is a record of
the decision, not the design exploration that led to it; if that exploration
is worth keeping, put it in a separate doc and reference it.

## Numbering and location

`docs/adr/NNNN-kebab-title.md` — zero-padded 4-digit number, assigned
sequentially at creation time in this repo's own ADR sequence (not tied to
any external list's numbering, e.g. PLAN.md's scoping-decision numbers).
Store every ADR in `docs/adr/`, the one central location — nowhere else.

## Process

One decision per ADR. If a change bundles more than one architecturally
significant choice, split it into separate ADRs rather than folding them
together. When a later decision reverses or replaces an earlier one, set the
old ADR's status to `Superseded by NNNN` and link forward to the new one —
never delete or silently rewrite an existing ADR.

## Before committing

Reference the ADR from the commit footer (`Refs: docs/adr/NNNN-title.md`,
per the git-workflow skill) when a commit implements or records the decision.
