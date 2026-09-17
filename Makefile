.PHONY: setup lint test typecheck fmt up down check-deploy-tools

GO_MODULES := services/load_gen lab/injector

CLUSTER_NAME := aiops2
KIND_CONFIG  := deploy/kind/kind-config.yaml
DEV_OVERLAY  := deploy/overlays/dev
KUBE_CONTEXT := kind-$(CLUSTER_NAME)

setup:
	uv sync --all-packages --dev
	pre-commit install --hook-type pre-commit --hook-type commit-msg

fmt:
	uv run ruff format .
	@for m in $(GO_MODULES); do gofmt -l -w $$m; done

lint:
	uv run ruff check .
	uv run ruff format --check .
	@for m in $(GO_MODULES); do \
		echo "== gofmt -l $$m =="; \
		out="$$(gofmt -l $$m)"; \
		if [ -n "$$out" ]; then echo "$$out"; exit 1; fi; \
		echo "== go vet $$m =="; \
		(cd $$m && go vet ./...) || exit 1; \
		echo "== golangci-lint $$m =="; \
		(cd $$m && golangci-lint run ./...) || exit 1; \
	done

typecheck:
	uv run mypy .

test:
	uv run pytest -m "not eval"
	@for m in $(GO_MODULES); do \
		echo "== go test -race $$m =="; \
		(cd $$m && go test -race ./...) || exit 1; \
	done

check-deploy-tools:
	@command -v docker >/dev/null 2>&1 || { \
		echo "error: no container runtime found. kind needs Docker (or Podman)."; \
		echo "  Install Docker Desktop: https://docs.docker.com/desktop/setup/install/mac-install/"; \
		echo "  or Colima:              brew install colima docker && colima start"; \
		exit 1; }
	@command -v kind >/dev/null 2>&1 || { \
		echo "error: kind not found. Install: brew install kind"; exit 1; }
	@command -v kubectl >/dev/null 2>&1 || { \
		echo "error: kubectl not found. Install: brew install kubectl"; exit 1; }

up: check-deploy-tools
	@if kind get clusters 2>/dev/null | grep -qx "$(CLUSTER_NAME)"; then \
		echo "kind cluster '$(CLUSTER_NAME)' already exists, skipping creation"; \
	else \
		kind create cluster --name $(CLUSTER_NAME) --config $(KIND_CONFIG); \
	fi
	kubectl --context $(KUBE_CONTEXT) apply -k $(DEV_OVERLAY)
	kubectl --context $(KUBE_CONTEXT) -n aiops2 rollout status deployment/otel-lgtm --timeout=180s
	@echo ""
	@echo "Grafana: http://localhost:3000"

down: check-deploy-tools
	kind delete cluster --name $(CLUSTER_NAME)
