import sys
from pathlib import Path
from typing import Any

import pytest

from vk import cli
from vk.approval import Caller
from vk.config import Config, ConfigError
from vk.llm import BudgetExceeded

CFG = Config(repo="o/r", github_token="t", model="m", clan_models={}, state_dir=Path("/x"))


class Tty:
    def isatty(self) -> bool:
        return True


class NoTty:
    def isatty(self) -> bool:
        return False


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def fake_vk(cfg: Config, task: str, caller: Caller, **_kw: Any) -> str:
        seen.update(task=task, caller=caller)
        return "done"

    monkeypatch.setattr(cli, "load_config", lambda: CFG)
    monkeypatch.setattr(cli, "run_vk", fake_vk)
    return seen


def test_issue_attended_on_tty(
    captured: dict[str, Any], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", Tty())
    assert cli.main(["issue", "7"]) == 0
    assert captured["caller"] == Caller(False, issue_number=7)
    assert "vk:needs-info" in captured["task"]
    assert capsys.readouterr().out.strip() == "done"


def test_unattended_forced_without_tty(
    captured: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "stdin", NoTty())
    assert cli.main(["review", "9"]) == 0
    assert captured["caller"] == Caller(True, pr_number=9)
    assert "github__replyToReviewComment" in captured["task"]


def test_unattended_flag_and_ci_fix(
    captured: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "stdin", Tty())
    assert cli.main(["ci-fix", "9", "--unattended"]) == 0
    assert captured["caller"] == Caller(True, pr_number=9)
    assert "2" in captured["task"] and "fix-attempt" in captured["task"]


@pytest.mark.parametrize("exc", [ConfigError("GITHUB_TOKEN is required."), BudgetExceeded("big")])
def test_errors_exit_nonzero(
    exc: Exception, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom() -> Config:
        raise exc

    monkeypatch.setattr(cli, "load_config", boom)
    assert cli.main(["issue", "1"]) != 0
    assert str(exc) in capsys.readouterr().err


def test_bad_args_exit() -> None:
    with pytest.raises(SystemExit):
        cli.main(["issue", "abc"])
