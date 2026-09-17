.PHONY: setup lint test typecheck fmt

GO_MODULES := services/load_gen lab/injector

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
