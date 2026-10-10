#!/usr/bin/env bash
# PostToolUse hook: auto-format Python files Claude edits. Never blocks the edit.
file=$(jq -r '.tool_input.file_path // empty')
case "$file" in
  *.py)
    uv run --quiet ruff check --fix --quiet "$file" || true
    uv run --quiet ruff format --quiet "$file" || true
    ;;
esac
exit 0
