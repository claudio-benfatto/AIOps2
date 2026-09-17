# 0006. Investigator is read-only and advisory

## Status
Accepted

## Context
An investigator that can act on the system it's diagnosing mixes two very
different claims: "it can find the root cause" and "it can safely act on
production." This project scopes to the first claim only, and safety
invariants elsewhere in the repo (fault state must stay hidden, tools must
be read-only) depend on the investigator having no side-effecting reach.

## Decision
The investigator only ever issues read/query calls (Prometheus, Loki, Tempo,
K8s API, `topology.yaml`) and recommends remediation as text in the RCA
output; it never executes remediation itself.

## Consequences
- The benchmark measures diagnostic accuracy in isolation, uninfluenced by
  any risk of the investigator changing system state mid-investigation.
- Tool implementations only need read-only contracts (GET/query), simplifying
  both the tools and their safety review.
- Automated remediation is explicitly out of scope for this version (see
  PLAN.md's "Later" list), not a capability gap to fill later within this
  project.
