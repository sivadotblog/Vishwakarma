# Single command contract for humans, Claude, CI, and the software factory.
# `make check` is the definition of done: it must pass before any PR merges.
# CI runs `check-python` and `check-web` as separate jobs; together they are `check`.

.PHONY: setup setup-python setup-web lint lint-python lint-web format typecheck \
	typecheck-python typecheck-web test build check check-python check-web

setup: setup-python setup-web

setup-python:
	uv sync --locked

setup-web:
	npm ci

lint: lint-python lint-web

lint-python:
	uv run ruff check
	uv run ruff format --check

lint-web:
	npm run lint -w web

format:
	uv run ruff check --fix
	uv run ruff format
	npm run format -w web

typecheck: typecheck-python typecheck-web

typecheck-python:
	uv run mypy

typecheck-web:
	npm run check -w web

test:
	uv run pytest

build:
	npm run build -w web

check-python: lint-python typecheck-python test

check-web: lint-web typecheck-web build

check: check-python check-web
