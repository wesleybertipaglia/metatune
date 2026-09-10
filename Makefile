.PHONY: help install dev test test-verbose lint format template-example clean run-help show

PY ?= python3
export PYTHONPATH := src:$(PYTHONPATH)

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## Install runtime dependencies
	$(PY) -m pip install -r requirements.txt

dev: ## Install package in editable mode + dev tools
	$(PY) -m pip install -e ".[dev]"

test: ## Run test suite
	$(PY) -m pytest -q

test-verbose: ## Run test suite with verbose output
	$(PY) -m pytest -v

lint: ## Syntax check (compileall) + ruff if available
	$(PY) -m compileall -q src/metatune tests
	@ruff check src/metatune tests 2>/dev/null || echo "(ruff not installed, skipped)"

format: ## Format code with ruff if available
	@ruff format src/metatune tests 2>/dev/null || echo "(ruff not installed, skipped)"

template-example: ## Generate an example template in ./examples
	$(PY) -m metatune template --output examples/metadata-template.json --force

run-help: ## Show CLI help
	$(PY) -m metatune --help

show: ## Show tags of a file: make show FILE=song.mp3
	$(PY) -m metatune show "$(FILE)"

clean: ## Remove caches and build artifacts
	rm -rf __pycache__ .pytest_cache .ruff_cache build dist *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
