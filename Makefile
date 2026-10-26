.DEFAULT_GOAL := help
.PHONY: help install lint test test-unit

VENV := server/.venv
PY := $(VENV)/bin/python

help: ## Shows the available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

$(PY):
	python3 -m venv $(VENV)

install: $(PY) ## Sets up the machine: server venv, dependencies, npm ci, pre-push hooks
	$(PY) -m pip install --quiet -r server/requirements-dev.txt
	npm --prefix client ci --no-audit --no-fund
	$(PY) -m pre_commit install
	$(PY) -m pre_commit install-hooks

lint: ## Lint of the server and the client
	cd server && .venv/bin/ruff check .
	npm --prefix client run lint
	npm --prefix client run typecheck

test-unit: ## Server unit tests (no container)
	cd server && .venv/bin/python -m pytest -m unit

test: ## All server tests (starts the test PostgreSQL if needed)
	cd server && .venv/bin/python -m pytest
