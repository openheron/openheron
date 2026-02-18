"""MCP toolset construction helpers for sentientagent_v2."""

from __future__ import annotations

import json
import os
from typing import Any

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    SseConnectionParams,
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from loguru import logger
from mcp import StdioServerParameters

_MCP_SERVERS_ENV = "SENTIENTAGENT_V2_MCP_SERVERS_JSON"


class SafeMcpToolset(McpToolset):
    """MCP toolset that degrades to an empty set on connection errors."""

    async def get_tools(self, *args: Any, **kwargs: Any) -> list[Any]:
        try:
            return await super().get_tools(*args, **kwargs)
        except Exception as exc:
            logger.warning("MCP toolset unavailable; continuing without MCP tools: {}", exc)
            return []


def _load_servers_from_env() -> dict[str, Any]:
    """Read and parse MCP servers map from environment."""
    raw = os.getenv(_MCP_SERVERS_ENV, "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        logger.warning("Invalid {} JSON, skipping MCP servers: {}", _MCP_SERVERS_ENV, exc)
        return {}
    if not isinstance(parsed, dict):
        logger.warning("{} must be a JSON object; got {}", _MCP_SERVERS_ENV, type(parsed).__name__)
        return {}
    return parsed


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _string_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(k): str(v) for k, v in value.items()}


def _pick(raw: dict[str, Any], snake: str, camel: str, default: Any = None) -> Any:
    if snake in raw:
        return raw[snake]
    if camel in raw:
        return raw[camel]
    return default


def build_mcp_toolsets(mcp_servers: dict[str, Any]) -> list[SafeMcpToolset]:
    """Build configured MCP toolsets.

    Supported per-server config keys:
    - `command` + `args` + `env` (stdio)
    - `url` (+ optional `headers`, `transport=sse|http`)
    - `toolFilter` / `tool_filter`
    - `toolNamePrefix` / `tool_name_prefix`
    - `requireConfirmation` / `require_confirmation`
    """
    toolsets: list[SafeMcpToolset] = []
    for server_name, raw_cfg in mcp_servers.items():
        if not isinstance(raw_cfg, dict):
            logger.warning("MCP server '{}' config must be an object; got {}", server_name, type(raw_cfg).__name__)
            continue

        command = str(raw_cfg.get("command", "") or "").strip()
        url = str(raw_cfg.get("url", "") or "").strip()
        args = _string_list(raw_cfg.get("args", []))
        env = _string_dict(raw_cfg.get("env", {}))
        headers = _string_dict(raw_cfg.get("headers", {})) or None
        transport = str(raw_cfg.get("transport", "") or "").strip().lower()

        if command:
            connection_params: Any = StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=command,
                    args=args,
                    env=env or None,
                ),
            )
        elif url:
            if transport == "sse" or url.lower().rstrip("/").endswith("/sse"):
                connection_params = SseConnectionParams(url=url, headers=headers)
            else:
                connection_params = StreamableHTTPConnectionParams(url=url, headers=headers)
        else:
            logger.warning("MCP server '{}' has neither command nor url; skipping", server_name)
            continue

        tool_filter = _pick(raw_cfg, "tool_filter", "toolFilter")
        tool_filter_list = _string_list(tool_filter) if isinstance(tool_filter, list) else None
        prefix = str(_pick(raw_cfg, "tool_name_prefix", "toolNamePrefix", "") or "").strip()
        if not prefix:
            prefix = f"mcp_{server_name}_"
        require_confirmation = bool(_pick(raw_cfg, "require_confirmation", "requireConfirmation", False))

        toolset = SafeMcpToolset(
            connection_params=connection_params,
            tool_filter=tool_filter_list,
            tool_name_prefix=prefix,
            require_confirmation=require_confirmation,
        )
        toolsets.append(toolset)
        logger.info("MCP server '{}' registered (prefix='{}')", server_name, prefix)

    return toolsets


def build_mcp_toolsets_from_env() -> list[SafeMcpToolset]:
    """Build MCP toolsets from `SENTIENTAGENT_V2_MCP_SERVERS_JSON`."""
    return build_mcp_toolsets(_load_servers_from_env())

