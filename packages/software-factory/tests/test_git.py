import subprocess
from pathlib import Path

import pytest

from software_factory.config import Config
from software_factory.git import (
    GitError,
    checkout_branch,
    clone_repo,
    commit_file,
    git_tools,
    push_branch,
    sanitize,
    validate_branch,
)

TOKEN = "ghs_supersecrettoken123456"


def sh(*args: str, cwd: Path | None = None) -> str:
    out = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)
    return out.stdout.strip()


def make_cfg(tmp_path: Path, setup: str | None = None) -> Config:
    return Config(
        repo="owner/name",
        github_token=TOKEN,
        model="m",
        station_models={},
        state_dir=tmp_path / "state",
        setup_command=setup,
    )


@pytest.fixture
def remote(tmp_path: Path) -> str:
    bare = tmp_path / "remote.git"
    sh("git", "init", "--bare", "-b", "main", str(bare))
    seed = tmp_path / "seed"
    sh("git", "clone", str(bare), str(seed))
    (seed / "README.md").write_text("hi\n")
    sh("git", "add", ".", cwd=seed)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "init", cwd=seed)
    sh("git", "push", "origin", "HEAD:main", cwd=seed)
    return f"file://{bare}"


@pytest.mark.parametrize("branch", ["factory/bug-x", "a", "feat_1.2/x-y"])
def test_validate_branch_accepts_plain_names(branch: str) -> None:
    assert validate_branch(branch) is None


@pytest.mark.parametrize(
    "branch",
    [
        "",
        "main",
        "master",
        "HEAD",
        "refs/heads/x",
        "a..b",
        "a//b",
        "-x",
        "a b",
        "x;rm",
        "x/",
        "$(x)",
    ],
)
def test_validate_branch_rejects(branch: str) -> None:
    assert validate_branch(branch) is not None


def test_sanitize_removes_token_and_header() -> None:
    text = f"fatal: {TOKEN} Authorization: Basic abcdefgh12345678 x-access-token:{TOKEN}"
    out = sanitize(text, TOKEN)
    assert TOKEN not in out
    assert "abcdefgh12345678" not in out


def test_clone_checkout_push_roundtrip(tmp_path: Path, remote: str) -> None:
    cfg = make_cfg(tmp_path, setup="touch .setup-ran")
    repo = clone_repo(cfg, remote_url=remote)
    assert repo.is_relative_to(cfg.state_dir / "work")
    assert (repo / ".setup-ran").exists()
    assert sh("git", "config", "--local", "user.name", cwd=repo) == "software-factory[bot]"

    sh("git", "checkout", "-b", "factory/feat", cwd=repo)
    sha = commit_file(repo, "factory/feat", "docs/log.md", "log\n", "add log")
    pushed = push_branch(cfg, repo, "factory/feat", remote_url=remote)
    assert pushed == {"branch": "factory/feat", "sha": sha, "success": True}

    other = clone_repo(cfg, remote_url=remote)
    got = checkout_branch(cfg, other, "factory/feat", remote_url=remote)
    assert got["success"] is True and got["sha"] == sha
    assert (other / "docs/log.md").read_text() == "log\n"


def test_push_refuses_main_and_missing_branch(tmp_path: Path, remote: str) -> None:
    cfg = make_cfg(tmp_path)
    repo = clone_repo(cfg, remote_url=remote)
    assert push_branch(cfg, repo, "main", remote_url=remote)["success"] is False
    missing = push_branch(cfg, repo, "factory/nope", remote_url=remote)
    assert missing["success"] is False
    assert TOKEN not in str(missing)


def test_token_never_in_git_config(tmp_path: Path, remote: str) -> None:
    cfg = make_cfg(tmp_path)
    repo = clone_repo(cfg, remote_url=remote)
    for config in [repo / ".git" / "config", *repo.glob(".git/**/config")]:
        assert TOKEN not in config.read_text()
    assert TOKEN not in sh("git", "config", "--list", "--show-origin", cwd=repo)


def test_github_clone_failure_is_sanitized(tmp_path: Path) -> None:
    """With no injected remote, the auth header is sent; a failure must not leak it."""
    cfg = make_cfg(tmp_path)
    cfg2 = Config(**{**cfg.__dict__, "repo": "invalid repo with spaces"})
    with pytest.raises(GitError) as exc:
        clone_repo(cfg2, remote_url="file:///nonexistent/repo.git")
    assert TOKEN not in str(exc.value)


def test_commit_file_rejects_traversal(tmp_path: Path, remote: str) -> None:
    repo = clone_repo(make_cfg(tmp_path), remote_url=remote)
    sh("git", "checkout", "-b", "factory/x", cwd=repo)
    with pytest.raises(GitError):
        commit_file(repo, "factory/x", "../evil.txt", "x", "m")
    with pytest.raises(GitError):
        commit_file(repo, "main", "a.txt", "x", "m")


def test_git_tools_surface(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    assert [t.name for t in git_tools(cfg, tmp_path, allow_push=False)] == ["checkout_branch"]
    tools = git_tools(cfg, tmp_path, allow_push=True)
    assert [t.name for t in tools] == ["checkout_branch", "push_branch"]
    assert tools[1].fn({"branch": "main"})["success"] is False


def test_validate_branch_rejects_trailing_newline() -> None:
    assert validate_branch("factory/x\n") is not None
