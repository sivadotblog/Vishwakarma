---
name: verify
description: Run the repo's definition-of-done checks (make check) and fix failures — lint, format, type errors, failing tests, broken Astro builds. Use before declaring any task complete, before opening or updating a PR, and when CI is red.
---

# Verify

`make check` from the repo root is the single source of truth. CI runs exactly `make setup && make check`, so if it passes locally it passes in CI.

## Loop

1. `make setup` if dependencies changed (or after a fresh checkout).
2. `make check`. It stops at the first failing stage, in this order:

| Stage | Command | Typical fix |
| --- | --- | --- |
| lint | `uv run ruff check` / `ruff format --check` | `make format`, then fix what remains by hand |
| typecheck | `uv run mypy` (strict) | Add real annotations. No `# type: ignore` / `Any` without a comment saying why |
| test | `uv run pytest` | Fix the code, not the test — unless the test encodes the old, intentionally changed behavior |
| build | `npm run build -w web` | Usually a bad sidebar `slug` or broken import |

Then fix the root cause, rerun only the failing stage (e.g. `uv run pytest apps/api/tests/test_x.py -q`), then rerun full `make check` once at the end.

## Rules

- Never skip, delete, or weaken a check to get green (no `-k` deselection, `xfail`, lowering mypy strictness, or editing CI).
- If a failure is pre-existing and unrelated to your change, say so explicitly with the output — don't silently fix or hide it.
- Report what you ran and the result. "Done" means `make check` exited 0.
