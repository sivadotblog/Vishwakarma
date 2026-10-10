---
paths:
  - "apps/api/**"
  - "pyproject.toml"
---

# Python conventions

- Python 3.12+ syntax: `X | None`, built-in generics (`list[str]`), `match` where it reads better.
- `mypy --strict` must pass: annotate every function, including tests and fixtures.
- Ruff decides formatting and import order — run `make format`, don't hand-format.
- Tests: pytest, plain functions and `assert`, fixtures over setup classes. A bug fix starts with a failing test.
- Raise specific exceptions; never bare `except:` or `except Exception: pass`.
