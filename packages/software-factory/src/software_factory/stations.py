"""The five stations as data: prompt, output schema, model and tool surface."""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from software_factory import git, llm
from software_factory.config import Config
from software_factory.schemas import (
    ANALYST_OUTPUT_SCHEMA,
    CLASSIFIER_OUTPUT_SCHEMA,
    IMPLEMENTER_OUTPUT_SCHEMA,
    RESEARCHER_OUTPUT_SCHEMA,
    REVIEWER_OUTPUT_SCHEMA,
)
from software_factory.tooling import Tool
from software_factory.tools import artifact_tools, harness_tools

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
class Station:
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
    """The target repo's own agent instructions, so stations follow its toolchain and rules."""
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


STATIONS: dict[str, Station] = {
    "classifier": Station("classifier", CLASSIFIER_OUTPUT_SCHEMA, False, _classifier),
    "researcher": Station("researcher", RESEARCHER_OUTPUT_SCHEMA, False, _researcher),
    "analyst": Station("analyst", ANALYST_OUTPUT_SCHEMA, True, _analyst),
    "implementer": Station("implementer", IMPLEMENTER_OUTPUT_SCHEMA, True, _implementer),
    "reviewer": Station("reviewer", REVIEWER_OUTPUT_SCHEMA, True, _reviewer),
}


def run_station(
    name: str,
    message: str,
    cfg: Config,
    *,
    complete: Callable[..., Any] | None = None,
    remote_url: str | None = None,
) -> dict[str, Any]:
    """Run one station to its structured output, in a fresh clone when it needs a repo.

    `complete` and `remote_url` are test seams (LLM call, git remote override).
    """
    station = STATIONS[name]
    repo_dir = git.clone_repo(cfg, remote_url=remote_url) if station.needs_repo else None
    try:
        # Stations without a repo get a placeholder dir only for tools that ignore it.
        tools = station.tools(cfg, repo_dir or Path.cwd(), remote_url)
        extra = {"complete": complete} if complete is not None else {}
        result = llm.run_agent(
            model=cfg.model_for(name),
            system=station.prompt(cfg, repo_dir),
            message=message,
            tools=tools,
            output_schema=station.schema,
            max_output_tokens=cfg.max_output_tokens,
            **extra,
        )
        return cast(dict[str, Any], result)
    finally:
        if repo_dir is not None:
            shutil.rmtree(repo_dir.parent, ignore_errors=True)
