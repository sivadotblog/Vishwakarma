"""Guards for rules the model follows from prompts, not code; they must not drift."""

from importlib.resources import files

from vk import cli


def vk_prompt() -> str:
    return (files("vk") / "prompts" / "vk.md").read_text()


def test_vk_stops_on_needs_clarification() -> None:
    text = vk_prompt()
    assert "needs_clarification" in text
    assert "stop the pipeline" in text


def test_vk_caps_revision_cycles_and_skips_pr() -> None:
    text = vk_prompt()
    assert f"at most {cli.MAX_REVIEW_CYCLES} revision cycles" in text
    assert "don't open a pull request" in text


def test_unattended_issue_task_posts_questions_and_never_asks() -> None:
    task = cli.issue_task(7, unattended=True)
    assert "vk:needs-info" in task
    assert "vk:blocked" in task
    assert "never ask" in task.lower()
    assert "Closes #7" in task
