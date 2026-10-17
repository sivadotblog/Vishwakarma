"""Tests for the tool-calling loop using a scripted fake `complete`."""

import json
import logging
from types import SimpleNamespace
from typing import Any

import pytest

from vk.llm import BudgetExceeded, SubmitError, run_agent
from vk.tooling import Tool, ToolError

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["ok", "bad"]},
        "note": {"type": ["string", "null"]},
    },
    "required": ["verdict", "note"],
}


def call(name: str, args: dict[str, Any], cid: str = "c1") -> SimpleNamespace:
    fn = SimpleNamespace(name=name, arguments=json.dumps(args))
    return SimpleNamespace(id=cid, function=fn)


def turn(
    calls: list[SimpleNamespace] | None = None,
    text: str | None = None,
    tokens: int = 10,
    prompt: int = 0,
) -> SimpleNamespace:
    msg = SimpleNamespace(content=text, tool_calls=calls or None)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=msg)],
        usage=SimpleNamespace(
            prompt_tokens=prompt, completion_tokens=tokens, total_tokens=prompt + tokens
        ),
    )


class Script:
    def __init__(self, *turns: SimpleNamespace) -> None:
        self.turns = list(turns)
        self.seen: list[list[dict[str, Any]]] = []

    def __call__(self, **kwargs: Any) -> SimpleNamespace:
        self.seen.append(list(kwargs["messages"]))
        return self.turns.pop(0)


def run(
    script: Script, tools: list[Tool], schema: dict[str, Any] | None, budget: int = 1000
) -> dict[str, Any] | str:
    return run_agent(
        model="m",
        system="s",
        message="go",
        tools=tools,
        output_schema=schema,
        max_output_tokens=budget,
        complete=script,
    )


ECHO = Tool("echo", "echo", {"type": "object"}, lambda a: {"got": a["x"]})


def test_tool_call_then_submit() -> None:
    script = Script(
        turn([call("echo", {"x": 1})]),
        turn([call("submit", {"verdict": "ok", "note": None})]),
    )
    assert run(script, [ECHO], SCHEMA) == {"verdict": "ok", "note": None}
    tool_msg = script.seen[1][-1]
    assert tool_msg["role"] == "tool" and json.loads(tool_msg["content"]) == {"got": 1}


def test_invalid_submit_is_retried() -> None:
    script = Script(
        turn([call("submit", {"verdict": "maybe", "note": None})]),
        turn([call("submit", {"verdict": "ok", "note": "x"})]),
    )
    assert run(script, [], SCHEMA) == {"verdict": "ok", "note": "x"}
    assert "must be one of" in script.seen[1][-1]["content"]


def test_invalid_submit_gives_up_after_three() -> None:
    bad = call("submit", {"verdict": "ok"})
    with pytest.raises(SubmitError):
        run(Script(turn([bad]), turn([bad]), turn([bad])), [], SCHEMA)


def test_budget_exceeded() -> None:
    with pytest.raises(BudgetExceeded):
        run(Script(turn(text="hi", tokens=50)), [], None, budget=10)


def test_tool_error_surfaced() -> None:
    def boom(_: dict[str, Any]) -> Any:
        raise ToolError("nope")

    script = Script(turn([call("boom", {})]), turn(text="done"))
    assert run(script, [Tool("boom", "b", {"type": "object"}, boom)], None) == "done"
    assert json.loads(script.seen[1][-1]["content"]) == {"error": "nope"}


def test_text_only_mode() -> None:
    assert run(Script(turn(text="final answer")), [], None) == "final answer"


def test_token_usage_logged(caplog: pytest.LogCaptureFixture) -> None:
    script = Script(
        turn([call("echo", {"x": 1})], tokens=5, prompt=100),
        turn(text="done", tokens=7, prompt=120),
    )
    with caplog.at_level(logging.INFO, logger="vk.llm"):
        run_agent(
            model="m",
            system="s",
            message="go",
            tools=[ECHO],
            output_schema=None,
            max_output_tokens=1000,
            complete=script,
            name="analyst",
        )
    lines = [r.getMessage() for r in caplog.records]
    assert (
        "llm analyst model=m turn=1 prompt_tokens=100 completion_tokens=5 total_tokens=105" in lines
    )
    assert (
        "llm analyst model=m turn=2 prompt_tokens=120 completion_tokens=7 total_tokens=127" in lines
    )
    assert "agent analyst tool=echo" in lines
    assert "agent analyst done turns=2 prompt_tokens=220 completion_tokens=12" in lines
