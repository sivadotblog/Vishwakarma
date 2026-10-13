"""VK: orchestrator prompt plus the tools it routes work with."""

import getpass
from collections.abc import Callable
from pathlib import Path
from typing import Any

from vk import llm
from vk.approval import Caller, Confirm, default_confirm
from vk.clans import CLANS, run_clan
from vk.config import Config
from vk.github import GitHub, github_tools
from vk.runlog import publish_run_log_tool
from vk.tooling import Tool, ToolError
from vk.tools import (
    artifact_tools,
    brain_tools,
    preference_tools,
    skill_tools,
)

VK_PROMPT = Path(__file__).parent / "prompts" / "vk.md"
_MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {"message": {"type": "string", "minLength": 1}},
    "required": ["message"],
    "additionalProperties": False,
}
_DESCRIPTIONS = {
    "classifier": "Classify the work item: type, priority, complexity, and whether it needs "
    "clarification.",
    "researcher": "Research facts the repository does not hold, with cited sources.",
    "analyst": "Analyze the repository and produce the plan and acceptance criteria.",
    "implementer": "Implement the plan in a fresh clone, push the feature branch, and report. "
    "Also used for revisions on an existing branch.",
    "reviewer": "Independently review the pushed branch against the acceptance criteria.",
}


def _clan_tool(
    name: str, cfg: Config, complete: Callable[..., Any] | None, remote_url: str | None
) -> Tool:
    def run(args: dict[str, Any]) -> dict[str, Any]:
        message = args.get("message")
        if not isinstance(message, str) or not message:
            raise ToolError("message is required.")
        return run_clan(name, message, cfg, complete=complete, remote_url=remote_url)

    desc = f"{_DESCRIPTIONS[name]} The message must be self-contained: the clan sees no history."
    return Tool(f"run_{name}", desc, _MESSAGE_SCHEMA, run)


def _gated_clear(tools: list[Tool], confirm: Confirm) -> list[Tool]:
    out = []
    for tool in tools:
        if tool.name == "clear_user_preferences":
            inner = tool.fn

            def gated(args: dict[str, Any], inner: Callable[..., Any] = inner) -> Any:
                if not confirm("Allow clear_user_preferences (permanently deletes them)?"):
                    raise ToolError("denied: clearing preferences was not approved")
                return inner(args)

            tool = Tool(tool.name, tool.description, tool.parameters, gated)
        out.append(tool)
    return out


def build_orchestrator_tools(
    cfg: Config,
    gh: GitHub,
    caller: Caller,
    confirm: Confirm | None = None,
    *,
    complete: Callable[..., Any] | None = None,
    remote_url: str | None = None,
) -> list[Tool]:
    ask = confirm or default_confirm
    user = None if caller.unattended else getpass.getuser()
    tools = [_clan_tool(name, cfg, complete, remote_url) for name in CLANS]
    tools += github_tools(gh, caller, ask)
    tools += _gated_clear(preference_tools(cfg, user), ask)
    tools += brain_tools(cfg, can_write=not caller.unattended)
    tools += artifact_tools(cfg, can_save=False)
    tools += skill_tools()
    tools.append(publish_run_log_tool(cfg, remote_url))
    return tools


def run_vk(
    cfg: Config,
    task: str,
    caller: Caller,
    *,
    gh: GitHub | None = None,
    confirm: Confirm | None = None,
    complete: Callable[..., Any] | None = None,
    remote_url: str | None = None,
) -> str:
    """Run VK on `task` and return its final reply."""
    gh = gh or GitHub(cfg)
    system = VK_PROMPT.read_text(encoding="utf-8").replace("{repo}", cfg.repo)
    extra = {"complete": complete} if complete is not None else {}
    reply = llm.run_agent(
        model=cfg.model_for("orchestrator"),
        system=system,
        message=task,
        tools=build_orchestrator_tools(
            cfg, gh, caller, confirm, complete=complete, remote_url=remote_url
        ),
        output_schema=None,
        max_output_tokens=cfg.max_output_tokens,
        **extra,
    )
    return str(reply)
