# Spec: vk (Vishwakarma)

## Context

Vishwakarma (VK) is a software factory: an orchestrator agent that moves a work item through
five clans (classifier, researcher, analyst, implementer and reviewer). The result is a
reviewed draft PR. VK is a lean, pip-installable Python package that works with any LLM
LiteLLM supports.

| Concern | Implementation |
|---|---|
| Agent runtime | Own tool-calling loop on `litellm.completion`; structured output through a final `submit` tool whose parameters are the clan's JSON schema |
| Models | LiteLLM model strings: env `VK_MODEL`, overridden per clan with `VK_MODEL_<CLAN>` |
| Intake | CLI subcommands, each injecting a fixed task text |
| GitHub tools | `github.py`: thin REST client on `requests` behind an allowlist, tools named `github__<name>` |
| Credentials | `GITHUB_TOKEN` env var |
| Isolation | A temp-dir clone per clan; the token goes in per-command `git -c http.extraHeader=…`, never into `.git/config`, and every command targets the literal `https://github.com/<repo>.git` URL, never `origin` |
| Harness | Python tools (bash, read, write, edit, web), run in the clan's clone |
| Storage (brain, preferences, artifacts) | Plain files under a local state dir |
| Approvals | Terminal `y/N` prompt when stdin is a TTY, otherwise denied (unattended) |

Beyond the core pipeline:
1. **Run log in the PR**: `docs/factory/issue-<N>.md` is committed to the PR branch. It holds
   the classification, the analysis (plan + acceptance criteria), the change summary,
   verification results and the reviewer verdict, plus a new section each review round.
2. **Review-comment loop**: `vk review <PR>` reads unanswered review comments.
   For each one it decides fixable or not. Fixable ones go through implementer → reviewer and
   get pushed to the same branch. Every comment gets a reply: what changed, or why it wasn't
   changed.

## Objective

A developer or CI job runs `vk issue 42` inside a checkout of a GitHub repo. The
factory:
- grounds the issue (dedupe, labels)
- classifies it, optionally researches, plans in its own clone, implements in its own clone,
  and pushes `vk/<type>-<slug>`
- has an independent reviewer judge the real diff, with up to 2 revision cycles
- commits the run log
- opens a **draft** PR (`Closes #42`)
- keeps the issue's labels and progress comments up to date, and finishes with a summary
  comment

Later, `vk review <PR>` handles reviewers' comments on that PR.

Users: maintainers of any GitHub repo (this monorepo first), with any LLM provider LiteLLM
supports.

## Capability map (Phase 0)

One package, built in this order. Arrows point one way.

| Module id | Responsibility | Depends on |
|---|---|---|
| `config` | Env/CLI config, repo detection from `origin`, state dir | — |
| `llm` | LiteLLM tool-calling loop, structured `submit`, token budget, compaction | config |
| `tools` | Harness tools (bash, read_file, write_file, edit_file, glob, grep, web_fetch, web_search), artifacts, brain, preferences, skills loader | config |
| `git` | Clone per clan, `checkout_branch`, `push_branch`, `validate_branch` | config |
| `github` | REST client + `github__*` tool wrappers + approval policies | config |
| `clans` | 5 clan definitions: prompt `.md`, schema, tool surface, model | llm, tools, git |
| `orchestrator` | VK prompt, `run_<clan>` tools, `publish_run_log` | clans, github |
| `cli` | Subcommands + injected task texts (issue / review / ci-fix) | orchestrator |

Build order: config → llm, tools, git, github → clans → orchestrator → cli.

## Behaviour by command

- `vk issue <N> [--unattended]`: the label-intake path. Never ask; if clarification is needed, post the questions on the issue and stop;
  deliver a draft PR. Status labels: `vk:in-progress` → `vk:pr-open` |
  `vk:needs-info` | `vk:blocked`. These are created if missing (the one label
  exception, flagged below), alongside the repo-vocabulary labels from the classifier.
- `vk review <PR>`: modelled on the CI-fix task:
  1. read the branch's `docs/factory/issue-<N>.md`
  2. list review comments and review bodies the factory hasn't replied to yet
  3. for each one, decide fix / won't-fix with a reason
  4. run implementer-revision → reviewer for the fixable batch on the same branch (≤2 cycles)
  5. reply in each comment's thread
  6. append a "Review round k" section to the log
- `vk ci-fix <PR>`: capped at 2 attempts, counted from
  attempt comments on the PR.
- `--unattended` is forced when stdin is not a TTY. In that mode, policies deny everything
  except labels, comments on its own issue/PR, closing/reopening issues, and draft PRs. When
  attended, reversible writes run, and shipping actions (mark ready, non-draft PR) ask `y/N`.
  Merge is not in the tool surface.

## Tech Stack

- Python ≥3.12, built with `uv_build` (same as `apps/api`)
- Runtime deps: **`litellm`** (any LLM) and **`requests`** (GitHub REST, web_fetch). Nothing
  else. git runs through `subprocess`; HTML→text uses stdlib `html.parser`. JSON-schema
  checks on `submit` are hand-rolled (required keys, enums, types), so there is no
  `jsonschema` dependency.
- Dev: the existing workspace dev group (ruff, mypy, pytest) + `types-requests`

## Commands

```
make setup                                   # uv sync --locked + npm ci (unchanged)
make check                                   # must pass; covers the new package once added to the workspace
uv run vk issue 42             # run from inside a checkout of the target repo
uv run vk review 57
uv run vk ci-fix 57
uv run pytest packages/vk      # package tests only
uv add --package vk <pkg>      # deps (needs a justification in the PR)
```

Env: `GITHUB_TOKEN` (required), `VK_MODEL` (required), `VK_MODEL_<CLAN>`,
the provider's API key under LiteLLM's standard name, `VK_SETUP_COMMAND`,
`VK_BRANCH_PREFIX` (`vk/`), `VK_STATE_DIR` (`~/.vk`),
`VK_MAX_OUTPUT_TOKENS` (100000).

## Project Structure

```
packages/vk/
  pyproject.toml            # name=vk, script vk = vk.cli:main
  README.md  SPEC.md
  src/vk/
    cli.py  config.py  llm.py  git.py  github.py  approval.py
    tools.py                # harness + artifacts + brain + preferences + skills
    orchestrator.py  clans.py  runlog.py  schemas.py
    prompts/                # vk.md + {classifier,researcher,analyst,implementer,reviewer}.md
    skills/                 # triaging-issues/, writing-quality/ (incl. references/)
  tests/                    # test_*.py, no network
```
Root changes: `pyproject.toml` (workspace member, mypy `files`, pytest `testpaths`, ruff
first-party), `AGENTS.md` table row.

## Code Style

Same as `apps/api`: 3.12 syntax, `mypy --strict`, ruff decides formatting, specific exceptions,
small modules, no classes where a function does the job. Example:

```python
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._/-]*[A-Za-z0-9])?$")
PROTECTED = {"main", "master"}


def validate_branch(branch: str) -> str | None:
    """Refusal reason, or None when the branch may reach a git command line."""
    if not BRANCH_PATTERN.match(branch) or ".." in branch or "//" in branch:
        return f'"{branch}" is not a valid branch name.'
    if branch.startswith("refs/") or branch == "HEAD":
        return f'"{branch}" is not a plain branch name.'
    if branch in PROTECTED:
        return f"Direct pushes to {branch} are not allowed. Push a feature branch."
    return None
```

## Testing Strategy

- pytest, plain functions, no network. `llm.run_agent` takes an injectable `complete` callable,
  so tests script LLM turns. The GitHub client takes an injectable `requests.Session`, faked
  with a tiny stub (no `responses` dep).
- Unit: `validate_branch`, approval policies (truth table per caller class), artifact-id containment, harness tools in `tmp_path`,
  schema validation in `submit`, run-log rendering.
- Pipeline: a scripted fake LLM + fake GitHub + a local bare git repo as the "remote" drives
  `issue` end to end (labels, push, run-log commit, draft PR) and `review` (fix one comment,
  explain another, replies posted).
- Manual smoke: a real run against a scratch repo before merging.

## Boundaries

- **Always**: draft PRs only; feature branches only (`validate_branch`); target the literal
  repo URL; never write the token to disk or into logs; `make check` green.
- **Ask first**: any dependency beyond litellm/requests; changing a prompt's substance;
  changing the trust/approval rules.
- **Never**: merge tools; push to main/master; store secrets in code.
- **Known risk (by design)**: the clans' `bash` tool runs repo code on the
  host with no sandbox. Run it in a disposable environment (e.g. a CI runner) for untrusted
  repos.

## Success Criteria

1. `pip install ./packages/vk` gives a working `vk` CLI; the only
   runtime deps are litellm and requests.
2. `vk issue N` on a scratch repo produces: classifier labels plus status labels
   on the issue, progress comments, a pushed `vk/*` branch containing
   `docs/factory/issue-N.md`, a draft PR with `Closes #N` and the acceptance-criteria checklist,
   and a closing summary comment.
3. Unclear issue → questions posted on the issue, no branch, `vk:needs-info`.
4. Reviewer `request_changes` loops ≤2 times; if it still fails there is no PR and the findings
   are posted on the issue.
5. `vk review PR` replies to every unanswered review comment (fixed with a commit
   reference, or an explanation), pushes fixes to the same branch, and appends a round to the
   log.
6. Switching `VK_MODEL` between two providers (e.g. `anthropic/…`, `openai/…`) works with
   no code change.
7. Unattended mode never calls a denied tool (test-enforced); there is no code path that pushes
   to main or merges.
8. `make check` passes.

## Open Questions

1. **Package path/name**: `packages/vk/`, PyPI `vk`, import
   `vk`. OK? (The PyPI name may be taken; checked at publish time.)
2. **Factory brain storage**: a local file under `VK_STATE_DIR` is lost on ephemeral CI
   runners. The alternative is committing it to the target repo (e.g. `docs/factory/BRAIN.md`).
   Default: local file.
3. **Researcher `web_search`**: Default is LiteLLM's
   provider-native web search where the model supports it, otherwise the tool reports itself
   unavailable. `web_fetch` uses requests.
4. **Status labels**: VK never invents labels otherwise, but `vk:*` status labels need creating
   once. OK to create them, or should status be comments only?
5. Add a "summarize PRs opened by others" path as `vk summarize <PR>`? Default: no.
