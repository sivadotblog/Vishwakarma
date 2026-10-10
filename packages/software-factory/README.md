# software-factory

Python port of the Vercel eve Software Factory ("Foreman"): an orchestrator agent moves a GitHub
issue through classifier, researcher, analyst, implementer and reviewer stations and delivers a
reviewed draft pull request. Any LLM supported by LiteLLM works. See [SPEC.md](SPEC.md).

## Install

```bash
pip install ./packages/software-factory      # or, in this monorepo: make setup
```

Runtime dependencies are `litellm` and `requests` only. `git` must be on the PATH.

## Environment

| Variable                    | Meaning                                                    |
| --------------------------- | ---------------------------------------------------------- |
| `GITHUB_TOKEN`              | Required. Token with repo, issues and pull request access. |
| `FACTORY_MODEL`             | Required. Any LiteLLM model string, e.g. `anthropic/...`.  |
| `FACTORY_MODEL_<STATION>`   | Optional per-station override (`ORCHESTRATOR`, `CLASSIFIER`, `RESEARCHER`, `ANALYST`, `IMPLEMENTER`, `REVIEWER`). |
| provider API key            | The provider's standard LiteLLM variable, e.g. `ANTHROPIC_API_KEY`. |
| `FACTORY_REPO`              | Optional `owner/name`; default is read from the `origin` remote. |
| `FACTORY_SETUP_COMMAND`     | Optional command run in each fresh clone (install deps).   |
| `FACTORY_BRANCH_PREFIX`     | Default `factory/`.                                        |
| `FACTORY_STATE_DIR`         | Default `~/.software-factory` (brain, artifacts, clones).  |
| `FACTORY_MAX_OUTPUT_TOKENS` | Output token budget per agent run, default 100000.         |

## Commands

Run from inside a checkout of the target repo. Each accepts `--unattended`, which is forced
whenever stdin is not a terminal.

```bash
software-factory issue 42      # triage, plan, implement, review, open a draft PR (Closes #42)
software-factory review 57     # answer review comments on a factory PR, push fixes, log the round
software-factory ci-fix 57     # fix failing CI on a factory PR (at most 2 attempts)
```

The run log is committed to the PR branch as `docs/factory/issue-<N>.md`. Exit codes: 0 success,
2 configuration error, 3 token budget exceeded.

## Example GitHub Actions workflow

Documentation only; copy it into your own repo's `.github/workflows/`.

```yaml
name: factory
on:
  issues:
    types: [labeled]
jobs:
  issue:
    if: github.event.label.name == 'factory'
    runs-on: ubuntu-latest
    permissions: { contents: write, issues: write, pull-requests: write }
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv tool install ./packages/software-factory
      - run: software-factory issue ${{ github.event.issue.number }} --unattended
        env:
          GITHUB_TOKEN: ${{ secrets.FACTORY_GITHUB_TOKEN }}
          FACTORY_MODEL: anthropic/claude-sonnet-4-5
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Warning: no sandbox

The stations' `bash` tool runs repository code directly on the host, with no sandbox (the
original used Vercel Sandbox). Run the factory only in a disposable environment such as a CI
runner, especially for untrusted repositories. The GitHub token is never written to disk or
passed to station commands.
