"""Environment-driven configuration shared by every module."""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

STATIONS = ("orchestrator", "classifier", "researcher", "analyst", "implementer", "reviewer")


class ConfigError(RuntimeError):
    """Missing or invalid configuration."""


@dataclass(frozen=True)
class Config:
    repo: str  # "owner/name"
    github_token: str
    model: str
    station_models: dict[str, str]
    state_dir: Path
    branch_prefix: str = "factory/"
    setup_command: str | None = None
    max_output_tokens: int = 100_000

    def model_for(self, station: str) -> str:
        return self.station_models.get(station, self.model)


_REMOTE = re.compile(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$")


def detect_repo(cwd: Path | None = None) -> str:
    """Return `owner/name` from the `origin` remote of the checkout at `cwd`."""
    out = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    match = _REMOTE.search(out.stdout.strip())
    if out.returncode != 0 or not match:
        raise ConfigError("Cannot detect a github.com repo from the `origin` remote.")
    return match.group(1)


def load_config(env: dict[str, str] | None = None, cwd: Path | None = None) -> Config:
    e = dict(os.environ) if env is None else env
    token = e.get("GITHUB_TOKEN")
    model = e.get("FACTORY_MODEL")
    if not token:
        raise ConfigError("GITHUB_TOKEN is required.")
    if not model:
        raise ConfigError("FACTORY_MODEL is required (any LiteLLM model string).")
    repo = e.get("FACTORY_REPO") or detect_repo(cwd)
    return Config(
        repo=repo,
        github_token=token,
        model=model,
        station_models={
            s: e[f"FACTORY_MODEL_{s.upper()}"]
            for s in STATIONS
            if e.get(f"FACTORY_MODEL_{s.upper()}")
        },
        state_dir=Path(e.get("FACTORY_STATE_DIR", "~/.software-factory")).expanduser(),
        branch_prefix=e.get("FACTORY_BRANCH_PREFIX", "factory/"),
        setup_command=e.get("FACTORY_SETUP_COMMAND") or None,
        max_output_tokens=int(e.get("FACTORY_MAX_OUTPUT_TOKENS", "100000")),
    )
