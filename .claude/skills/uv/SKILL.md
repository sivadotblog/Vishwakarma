---
name: uv
description: Manage the Python side of this monorepo with uv — add/remove/upgrade dependencies, run Python tools and scripts, sync the environment, add a new workspace package, or fix uv.lock conflicts. Use for any Python dependency or environment task, and whenever you'd otherwise reach for pip, poetry, venv, or python -m.
---

# uv in this repo

The repo root is a **virtual uv workspace**: root `pyproject.toml` has no `[project]`, only `[tool.uv.workspace]`, shared dev tools (`[dependency-groups] dev`), and ruff/mypy/pytest config. Members live under `apps/` (today: `apps/api`, package name `api`). One `uv.lock` at the root covers everything. Python version is pinned in `.python-version`.

## Commands — always run from the repo root

| Task | Command |
| --- | --- |
| Install / sync everything | `uv sync` (CI uses `uv sync --locked`) |
| Runtime dep for the API | `uv add --package api <pkg>` |
| Dev tool for the whole repo | `uv add --dev <pkg>` (goes to root `dev` group) |
| Remove a dep | `uv remove --package api <pkg>` |
| Upgrade one dep | `uv lock --upgrade-package <pkg>` then `uv sync` |
| Run a tool / script | `uv run <cmd>` — e.g. `uv run pytest apps/api/tests/test_x.py -q` |
| One-off tool, not a dep | `uvx <tool>` |
| What depends on X | `uv tree --invert --package <pkg>` |

## Rules

- Never `pip install`, never activate `.venv` manually, never call bare `python` — use `uv run`.
- Never hand-edit `uv.lock`. On a merge conflict in it: take either side, then run `uv lock` and commit the result.
- Dependency changes always commit `pyproject.toml` **and** `uv.lock` together; `uv sync --locked` in CI fails otherwise.
- Prefer a lower-bound (`>=x.y`) as `uv add` writes it; don't pin exact versions unless an issue requires it.

## Adding a new workspace package

```bash
uv init --package --name <name> --no-workspace apps/<name>
rm apps/<name>/.python-version            # the root pin applies
```

Then add `"apps/<name>"` to `members` in the root `[tool.uv.workspace]`, add its `src`/`tests` paths to `[tool.mypy] files` and `[tool.pytest.ini_options] testpaths`, add the package name to ruff `known-first-party`, and run `uv sync` + `make check`.

## Verify

`make check` from the root must pass after any change.
