"""DeepSeek-specific LiteLLM helpers."""

from __future__ import annotations

import copy
from typing import Any

from google.adk.models.lite_llm import LiteLLMClient


def _enforce_strict_tool_schema(schema: dict[str, Any]) -> None:
    """Mutate a JSON schema into the shape required by strict tool calls."""
    if not isinstance(schema, dict):
        return

    if "$ref" in schema:
        for key in list(schema.keys()):
            if key != "$ref":
                del schema[key]
        return

    if schema.get("type") == "object":
        properties = schema.setdefault("properties", {})
        if isinstance(properties, dict):
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())

    for definitions_key in ("$defs", "definitions"):
        definitions = schema.get(definitions_key, {})
        if isinstance(definitions, dict):
            for definition in definitions.values():
                if isinstance(definition, dict):
                    _enforce_strict_tool_schema(definition)

    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        for property_schema in properties.values():
            if isinstance(property_schema, dict):
                _enforce_strict_tool_schema(property_schema)

    for combinator in ("anyOf", "oneOf", "allOf"):
        entries = schema.get(combinator, [])
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    _enforce_strict_tool_schema(entry)

    items = schema.get("items")
    if isinstance(items, dict):
        _enforce_strict_tool_schema(items)
    elif isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                _enforce_strict_tool_schema(item)


def make_deepseek_strict_tools(
    tools: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    """Return LiteLLM tool definitions marked for DeepSeek strict tool calls."""
    if not tools:
        return tools

    strict_tools = copy.deepcopy(tools)
    for tool in strict_tools:
        if not isinstance(tool, dict) or tool.get("type") != "function":
            continue
        function = tool.get("function")
        if not isinstance(function, dict):
            continue
        function["strict"] = True
        parameters = function.get("parameters")
        if isinstance(parameters, dict):
            _enforce_strict_tool_schema(parameters)
    return strict_tools


class DeepSeekStrictToolLiteLLMClient(LiteLLMClient):
    """LiteLLM client that enables DeepSeek strict tool calling."""

    async def acompletion(
        self,
        model: str,
        messages: list[Any],
        tools: list[dict[str, Any]] | None,
        **kwargs: Any,
    ) -> Any:
        """Call LiteLLM asynchronously after marking tool schemas strict."""
        return await super().acompletion(
            model=model,
            messages=messages,
            tools=make_deepseek_strict_tools(tools),
            **kwargs,
        )

    def completion(
        self,
        model: str,
        messages: list[Any],
        tools: list[dict[str, Any]] | None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Call LiteLLM synchronously after marking tool schemas strict."""
        return super().completion(
            model=model,
            messages=messages,
            tools=make_deepseek_strict_tools(tools),
            stream=stream,
            **kwargs,
        )
