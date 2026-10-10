"""Guards for rules the model follows from prompts, not code; they must not drift."""

from importlib.resources import files

from software_factory import cli


def foreman() -> str:
    return (files("software_factory") / "prompts" / "foreman.md").read_text()


def test_foreman_stops_on_needs_clarification() -> None:
    text = foreman()
    assert "needs_clarification" in text
    assert "stop the pipeline" in text


def test_foreman_caps_revision_cycles_and_skips_pr() -> None:
    text = foreman()
    assert f"at most {cli.MAX_REVIEW_CYCLES} revision cycles" in text
    assert "don't open a pull request" in text


def test_unattended_issue_task_posts_questions_and_never_asks() -> None:
    task = cli.issue_task(7, unattended=True)
    assert "factory:needs-info" in task
    assert "factory:blocked" in task
    assert "never ask" in task.lower()
    assert "Closes #7" in task
