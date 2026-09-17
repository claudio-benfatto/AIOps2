# 0002. Scripted target-agent LLM, real investigator LLM

## Status
Accepted

## Context
The target agent needs to produce realistic incident cascades (e.g. search
latency → retries → more steps → larger context → higher TTFT), and those
cascades need to emerge from mechanics rather than being hard-coded so the
lab's evidence stays honest (invariant 4). Only one LLM in the system needs
to reason under uncertainty for the claim this project makes: the
investigator.

## Decision
`llm-sim` returns tool-call decisions for the target agent from a
deterministic policy (retrieve → search → answer; retry on tool error;
etc.), not a real LLM. Only the investigator calls a real LLM API.

## Consequences
- Cascading failures are reproducible and attributable to mechanics, not to
  LLM sampling variance.
- The target system's behavior stays deterministic under a seed, keeping
  benchmark runs comparable.
- The investigator remains the only component whose real-LLM behavior needs
  to be measured, bounded, and reported on.
