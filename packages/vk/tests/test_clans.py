from pathlib import Path

from vk.clans import CLANS, MAX_REPO_INSTRUCTIONS
from vk.config import Config

CFG = Config(repo="o/r", github_token="t", model="m", clan_models={}, state_dir=Path("/x"))


def test_repo_instruction_files_are_injected(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("Use uv, never pip.")
    (tmp_path / "CLAUDE.md").write_text("Run make check before done.")

    prompt = CLANS["implementer"].prompt(CFG, tmp_path)

    assert "Use uv, never pip." in prompt
    assert "Run make check before done." in prompt
    assert prompt.index("AGENTS.md") < prompt.index("CLAUDE.md")


def test_no_section_without_instruction_files(tmp_path: Path) -> None:
    assert "Repository instructions" not in CLANS["analyst"].prompt(CFG, tmp_path)


def test_clans_without_a_repo_get_no_section() -> None:
    assert "Repository instructions" not in CLANS["classifier"].prompt(CFG, None)


def test_long_instruction_files_are_truncated(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("x" * (MAX_REPO_INSTRUCTIONS + 500))

    prompt = CLANS["reviewer"].prompt(CFG, tmp_path)

    assert "x" * MAX_REPO_INSTRUCTIONS in prompt
    assert "x" * (MAX_REPO_INSTRUCTIONS + 1) not in prompt
    assert "[truncated]" in prompt


def test_analyst_is_told_to_read_nested_instruction_files() -> None:
    assert "AGENTS.md" in CLANS["analyst"].prompt(CFG, Path("/nowhere"))
