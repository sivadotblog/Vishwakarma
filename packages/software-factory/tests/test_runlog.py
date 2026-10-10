from software_factory.runlog import render_review_round, render_run_log

DATA = {
    "classification": {
        "type": "bug",
        "priority": "high",
        "complexity": "small",
        "affected_area": "api",
        "summary": "Reset emails are sent twice.",
    },
    "analysis": {
        "problem_statement": "Duplicate sends.",
        "approach": "Dedupe on token.",
        "plan": ["Add a guard", "Add a test"],
        "acceptance_criteria": ["Only one email is sent", "A test covers it"],
    },
    "implementation": {
        "branch": "factory/bug-dedupe",
        "base": "main",
        "change_summary": [{"path": "a.py", "change": "guard"}],
        "verification": [{"command": "pytest", "result": "passed"}],
        "deviations": ["Used a set instead of a dict"],
    },
    "review": {
        "verdict": "approve",
        "summary": "Looks right.",
        "criteria_results": [
            {"criterion": "Only one email is sent", "pass": True, "evidence": "diff"},
            {"criterion": "A test covers it", "pass": False, "evidence": "none found"},
        ],
        "blocking_findings": [],
        "suggestions": [],
    },
}


def test_render_run_log_sections() -> None:
    text = render_run_log(42, DATA)
    for heading in ("## Summary", "## Classification", "## Analysis", "## Implementation"):
        assert heading in text
    assert "## Review\n" in text
    assert "issue #42" in text
    assert "- [x] Only one email is sent" in text
    assert "- [ ] A test covers it" in text
    assert "1. Add a guard" in text
    assert "- `pytest`: passed" in text
    assert "Used a set instead of a dict" in text
    assert "Verdict: **approve**" in text


def test_render_review_round() -> None:
    text = render_review_round(2, {"notes": "Fixed c1, explained c2.", "review": DATA["review"]})
    assert "## Review round 2" in text
    assert "Fixed c1, explained c2." in text
    assert "Verdict: **approve**" in text
