"""Tests for MCP toolset registry helpers."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from google.adk.tools.mcp_tool.mcp_session_manager import (
    SseConnectionParams,
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)

from sentientagent_v2.mcp_registry import _MCP_SERVERS_ENV, build_mcp_toolsets, build_mcp_toolsets_from_env


class McpRegistryTests(unittest.TestCase):
    def test_build_mcp_toolsets_stdio(self) -> None:
        toolsets = build_mcp_toolsets(
            {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                }
            }
        )
        self.assertEqual(len(toolsets), 1)
        self.assertIsInstance(toolsets[0]._connection_params, StdioConnectionParams)
        self.assertEqual(toolsets[0].tool_name_prefix, "mcp_filesystem_")

    def test_build_mcp_toolsets_sse(self) -> None:
        toolsets = build_mcp_toolsets(
            {
                "remote": {
                    "url": "https://example.com/sse",
                }
            }
        )
        self.assertEqual(len(toolsets), 1)
        self.assertIsInstance(toolsets[0]._connection_params, SseConnectionParams)

    def test_build_mcp_toolsets_streamable_http(self) -> None:
        toolsets = build_mcp_toolsets(
            {
                "remote": {
                    "url": "https://example.com/mcp",
                    "headers": {"Authorization": "Bearer t"},
                    "toolFilter": ["search"],
                    "toolNamePrefix": "x_",
                }
            }
        )
        self.assertEqual(len(toolsets), 1)
        self.assertIsInstance(toolsets[0]._connection_params, StreamableHTTPConnectionParams)
        self.assertEqual(toolsets[0].tool_name_prefix, "x_")

    def test_build_mcp_toolsets_from_env_invalid_json(self) -> None:
        with patch.dict(os.environ, {_MCP_SERVERS_ENV: "{bad json"}, clear=False):
            toolsets = build_mcp_toolsets_from_env()
        self.assertEqual(toolsets, [])

    def test_build_mcp_toolsets_skips_invalid_server_config(self) -> None:
        toolsets = build_mcp_toolsets({"bad": "oops"})
        self.assertEqual(toolsets, [])


if __name__ == "__main__":
    unittest.main()
