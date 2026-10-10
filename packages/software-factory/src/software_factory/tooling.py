"""The one shared tool shape: every module that exposes a tool returns `Tool` objects."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ToolFn = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema for the arguments object
    fn: ToolFn  # returns JSON-serialisable data; raise ToolError for model-visible failures


class ToolError(Exception):
    """Failure whose message is returned to the model as the tool result."""
