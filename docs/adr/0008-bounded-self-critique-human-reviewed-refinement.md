# 0008. Bounded investigator self-critique, human-reviewed refinement

## Status
Accepted

## Context
An investigator that only ever runs forward to `submit_rca` has no check on
its own evidence sufficiency, internal consistency, or confidence
calibration before committing to an answer — the kind of self-check a real
investigator would need, without an oracle. But letting that self-check
trigger unbounded revision would make cost and wall-clock time incomparable
across benchmark runs, and letting prompt/ledger-rule changes happen
automatically would break attribution of results to a specific, versioned
investigator.

## Decision
Before `submit_rca`, run exactly one bounded critic pass (a second LLM call,
no access to ground truth) that may trigger at most one revision, within the
same tool/token/time budgets as the rest of the run. The critique score and
text are attached to the RCA output and exported as investigator OTel
logs/metrics. Continuous refinement — editing the investigator's prompt or
hypothesis-ledger rules based on aggregated critique scores — stays a human
workflow between runs, committed as an ordinary code change, never automated
within or across runs.

## Consequences
- Every benchmark number stays attributable to a specific, versioned
  investigator (no autonomous self-modification).
- Self-critique cost is bounded and predictable: ~+3h in M3 (critic call,
  revise loop, RCA schema field) and ~+1h in M4 (capturing the score per
  run), moving the total budget from 60h to ~64h.
- Supersedes and absorbs the earlier stretch item "LLM-as-judge scoring of
  the causal chain" — it's now core scope, not stretch.
- Deliberately stops short of autonomous operation, consistent with the
  project's "Later" scope boundary.
