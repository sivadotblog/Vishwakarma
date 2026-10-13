"""The five clans as data: prompt, output schema, model and tool surface."""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from vk import git, llm
from vk.config import Config
from vk.schemas import (
    ANALYST_OUTPUT_SCHEMA,
    CLASSIFIER_OUTPUT_SCHEMA,
    IMPLEMENTER_OUTPUT_SCHEMA,
    RESEARCHER_OUTPUT_SCHEMA,
    REVIEWER_OUTPUT_SCHEMA,
)
from vk.tooling import Tool
from vk.tools import artifact_tools, harness_tools

PROMPTS_DIR = Path(__file__).parent / "prompts"
# Agent instruction files a target repo may carry at its root, in injection order.
REPO_INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md")
MAX_REPO_INSTRUCTIONS = 20_000  # characters per file

ToolBuilder = Callable[[Config, Path, str | None], list[Tool]]


def _classifier(_cfg: Config, _repo: Path, _remote: str | None) -> list[Tool]:
    return []


def _researcher(cfg: Config, repo: Path, _remote: str | None) -> list[Tool]:
    web = [t for t in harness_tools(repo, read_only=True, web=True) if t.name == "web_fetch"]
    return [*web, *artifact_tools(cfg, can_save=True)]


def _analyst(cfg: Config, repo: Path, _remote: str | None) -> list[Tool]:
    return [*harness_tools(repo, read_only=True, web=False), *artifact_tools(cfg, can_save=True)]


def _implementer(cfg: Config, repo: Path, remote: str | None) -> list[Tool]:
    return [
        *harness_tools(repo, read_only=False, web=False),
        *git.git_tools(cfg, repo, allow_push=True, remote_url=remote),
        *artifact_tools(cfg, can_save=False),
    ]


def _reviewer(cfg: Config, repo: Path, remote: str | None) -> list[Tool]:
    return [
        *harness_tools(repo, read_only=True, web=False),
        *git.git_tools(cfg, repo, allow_push=False, remote_url=remote),
        *artifact_tools(cfg, can_save=False),
    ]


@dataclass(frozen=True)
class Clan:
    name: str
    schema: dict[str, Any]
    needs_repo: bool
    tools: ToolBuilder

    def prompt(self, cfg: Config, repo_dir: Path | None) -> str:
        text = (PROMPTS_DIR / f"{self.name}.md").read_text(encoding="utf-8")
        text = text.replace("{repo}", cfg.repo)
        text = text.replace("{repo_dir}", str(repo_dir) if repo_dir else "")
        return text + repo_instructions(repo_dir) if repo_dir else text


def repo_instructions(repo_dir: Path) -> str:
    """The target repo's own agent instructions, so clans follow its toolchain and rules."""
    sections = []
    for name in REPO_INSTRUCTION_FILES:
        path = repo_dir / name
        if not path.is_file():
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        if len(body) > MAX_REPO_INSTRUCTIONS:
            body = body[:MAX_REPO_INSTRUCTIONS] + "\n[truncated]"
        sections.append(f"### {name}\n\n{body.strip()}")
    if not sections:
        return ""
    header = (
        "\n\n## Repository instructions\n\n"
        "The target repository ships these instructions for agents working in it. Follow them:"
        " they decide the package manager, the check commands, and the hard rules, and they"
        " override your own habits.\n\n"
    )
    return header + "\n\n".join(sections) + "\n"


CLANS: dict[str, Clan] = {
    "classifier": Clan("classifier", CLASSIFIER_OUTPUT_SCHEMA, False, _classifier),
    "researcher": Clan("researcher", RESEARCHER_OUTPUT_SCHEMA, False, _researcher),
    "analyst": Clan("analyst", ANALYST_OUTPUT_SCHEMA, True, _analyst),
    "implementer": Clan("implementer", IMPLEMENTER_OUTPUT_SCHEMA, True, _implementer),
    "reviewer": Clan("reviewer", REVIEWER_OUTPUT_SCHEMA, True, _reviewer),
}


def run_clan(
    name: str,
    message: str,
    cfg: Config,
    *,
    complete: Callable[..., Any] | None = None,
    remote_url: str | None = None,
) -> dict[str, Any]:
    """Run one clan to its structured output, in a fresh clone when it needs a repo.

    `complete` and `remote_url` are test seams (LLM call, git remote override).
    """
    clan = CLANS[name]
    repo_dir = git.clone_repo(cfg, remote_url=remote_url) if clan.needs_repo else None
    try:
        # Clans without a repo get a placeholder dir only for tools that ignore it.
        tools = clan.tools(cfg, repo_dir or Path.cwd(), remote_url)
        extra = {"complete": complete} if complete is not None else {}
        result = llm.run_agent(
            model=cfg.model_for(name),
            system=clan.prompt(cfg, repo_dir),
            message=message,
            tools=tools,
            output_schema=clan.schema,
            max_output_tokens=cfg.max_output_tokens,
            **extra,
        )
        return cast(dict[str, Any], result)
    finally:
        if repo_dir is not None:
            shutil.rmtree(repo_dir.parent, ignore_errors=True)
