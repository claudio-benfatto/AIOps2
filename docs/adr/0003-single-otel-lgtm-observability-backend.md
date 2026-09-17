# 0003. Single all-in-one observability backend (otel-lgtm)

## Status
Accepted

## Context
The target system, the lab, and the investigator all need a shared
observability backend: metrics, logs, traces, and a way to browse them.
Wiring up Prometheus, Loki, Tempo, and Grafana as separate deployments is a
day of integration work that proves nothing about the investigator's ability
to diagnose incidents.

## Decision
Deploy the `grafana/otel-lgtm` image (OTel Collector + Prometheus + Loki +
Tempo + Grafana bundled together) as a single deployment for the whole
system.

## Consequences
- One deployment to run and reason about instead of four separately wired
  services, freeing budget for the target system and investigator.
- Prometheus/Loki/Tempo/Grafana APIs stay standard, so investigator tools
  (PromQL, LogQL, Tempo search) work the same as against a hand-wired stack.
- Scaling or hardening this backend for anything beyond a single-cluster lab
  is out of scope — it's not meant to be production-representative.
