# Single command contract for humans, Claude, CI, and the software factory.
# `make check` is the definition of done: it must pass before any PR merges.

.PHONY: setup lint format typecheck test build check

setup:
	uv sync --locked
	npm ci

lint:
	uv run ruff check
	uv run ruff format --check

format:
	uv run ruff check --fix
	uv run ruff format

typecheck:
	uv run mypy
	npm run check -w web

test:
	uv run pytest

build:
	npm run build -w web

check: lint typecheck test build
