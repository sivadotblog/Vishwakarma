"""LiteLLM tool-calling loop with a synthetic `submit` tool for structured output."""

import json
import logging
from collections.abc import Callable
from typing import Any

import litellm

from vk.tooling import Tool

log = logging.getLogger(__name__)

MAX_SUBMIT_ATTEMPTS = 3
SUBMIT = "submit"
_TYPES: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
    "array": list,
    "object": dict,
    "null": type(None),
}


class BudgetExceeded(RuntimeError):
    """The agent spent more output tokens than allowed."""


class SubmitError(RuntimeError):
    """The model never produced a valid structured result."""


def validate(value: Any, schema: dict[str, Any], path: str = "$") -> str | None:
    """Return the first schema violation as text, or None when `value` conforms."""
    types = schema.get("type")
    if types is not None:
        names = [types] if isinstance(types, str) else types
        ok = any(
            isinstance(value, _TYPES[n])
            and not (isinstance(value, bool) and n in ("integer", "number"))
            for n in names
        )
        if not ok:
            return f"{path}: expected {' or '.join(names)}, got {type(value).__name__}"
    if "enum" in schema and value not in schema["enum"]:
        return f"{path}: must be one of {schema['enum']}"
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                return f"{path}: missing required key '{key}'"
        for key, sub in schema.get("properties", {}).items():
            if key in value and (err := validate(value[key], sub, f"{path}.{key}")):
                return err
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            return f"{path}: needs at least {schema['minItems']} item(s)"
        if "items" in schema:
            for i, item in enumerate(value):
                if err := validate(item, schema["items"], f"{path}[{i}]"):
                    return err
    return None


def _spec(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    fn = {"name": name, "description": description, "parameters": parameters}
    return {"type": "function", "function": fn}


def _run_tool(tool: Tool | None, raw_args: str) -> str:
    if tool is None:
        log.warning("unknown tool requested")
        return json.dumps({"error": "unknown tool"})
    try:
        args = json.loads(raw_args or "{}")
        result = tool.fn(args)
    except Exception as exc:  # tool failures are model-visible by design
        log.warning("tool %s failed: %s", tool.name, exc)
        return json.dumps({"error": str(exc)})
    return result if isinstance(result, str) else json.dumps(result, default=str)


def run_agent(
    *,
    model: str,
    system: str,
    message: str,
    tools: list[Tool],
    output_schema: dict[str, Any] | None,
    max_output_tokens: int,
    complete: Callable[..., Any] = litellm.completion,
    name: str = "agent",
) -> dict[str, Any] | str:
    """Run the loop; return the submitted object (schema mode) or the final text."""
    by_name = {t.name: t for t in tools}
    specs = [_spec(t.name, t.description, t.parameters) for t in tools]
    if output_schema is not None:
        desc = "Submit your final result. Call this exactly once when you are done."
        specs.append(_spec(SUBMIT, desc, output_schema))
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]
    spent = 0
    failures = 0
    turns = 0
    prompt_total = 0
    try:
        while True:
            resp = complete(model=model, messages=messages, tools=specs or None)
            turns += 1
            prompt = getattr(resp.usage, "prompt_tokens", 0) or 0
            completion = getattr(resp.usage, "completion_tokens", 0) or 0
            total = getattr(resp.usage, "total_tokens", 0) or 0
            prompt_total += prompt
            spent += completion
            log.info(
                "llm %s model=%s turn=%d prompt_tokens=%d completion_tokens=%d total_tokens=%d",
                name,
                model,
                turns,
                prompt,
                completion,
                total,
            )
            if spent > max_output_tokens:
                raise BudgetExceeded(f"{spent} output tokens exceeds budget {max_output_tokens}")
            msg = resp.choices[0].message
            calls = msg.tool_calls or []
            entry: dict[str, Any] = {"role": "assistant", "content": msg.content}
            if calls:
                entry["tool_calls"] = [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.function.name, "arguments": c.function.arguments},
                    }
                    for c in calls
                ]
            messages.append(entry)
            if not calls:
                if output_schema is None:
                    return msg.content or ""
                failures += 1
                log.warning("agent %s stopped without calling submit", name)
                if failures >= MAX_SUBMIT_ATTEMPTS:
                    raise SubmitError("model stopped without calling submit")
                messages.append({"role": "user", "content": f"Finish by calling `{SUBMIT}`."})
                continue
            for call in calls:
                tool_name, raw = call.function.name, call.function.arguments
                if output_schema is not None and tool_name == SUBMIT:
                    try:
                        result = json.loads(raw or "{}")
                        error = validate(result, output_schema)
                    except json.JSONDecodeError as exc:
                        result, error = None, f"invalid JSON: {exc}"
                    if error is None:
                        return result  # type: ignore[no-any-return]
                    failures += 1
                    log.warning("agent %s invalid submit: %s", name, error)
                    if failures >= MAX_SUBMIT_ATTEMPTS:
                        raise SubmitError(f"invalid submit after {failures} attempts: {error}")
                    content = json.dumps({"error": f"Invalid submit, fix and call again: {error}"})
                else:
                    log.info("agent %s tool=%s", name, tool_name)
                    log.debug("agent %s tool=%s args=%s", name, tool_name, raw)
                    content = _run_tool(by_name.get(tool_name), raw)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
    finally:
        log.info(
            "agent %s done turns=%d prompt_tokens=%d completion_tokens=%d",
            name,
            turns,
            prompt_total,
            spent,
        )
