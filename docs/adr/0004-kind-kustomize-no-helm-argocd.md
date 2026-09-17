# 0004. kind + Kustomize, no Helm/Argo CD

## Status
Accepted

## Context
The investigator's evidence includes Kubernetes-level signals: rollouts,
restarts, and events. A real Kubernetes API is therefore part of the system
under test, not just a deployment convenience. GitOps tooling (Helm charts,
Argo CD) adds packaging and sync machinery that doesn't change what evidence
the investigator can observe.

## Decision
Run the target system and observability stack on `kind` using plain
Kustomize bases/overlays; no Helm charts, no Argo CD.

## Consequences
- Kubernetes stays in the loop as a real evidence source (rollouts,
  restarts, events) without extra GitOps tooling to install, learn, or
  debug.
- Deploy manifests are plain YAML, kept simple enough to read end-to-end in
  `deploy/`.
- No templated chart reuse or automated sync — acceptable since this is a
  single-cluster lab, not a multi-environment deployment.
