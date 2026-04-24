"""Tests for DeepSeek LiteLLM helpers."""

from __future__ import annotations

import unittest

from openppx.core.deepseek_litellm import make_deepseek_strict_tools


class DeepSeekLiteLlmTests(unittest.TestCase):
    def test_make_deepseek_strict_tools_marks_functions_and_schemas(self) -> None:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "filters": {
                                "type": "object",
                                "properties": {
                                    "limit": {"type": "integer"},
                                },
                            },
                        },
                    },
                },
            }
        ]

        strict_tools = make_deepseek_strict_tools(tools)

        self.assertIsNot(strict_tools, tools)
        function = strict_tools[0]["function"]
        self.assertTrue(function["strict"])
        params = function["parameters"]
        self.assertFalse(params["additionalProperties"])
        self.assertEqual(params["required"], ["filters", "query"])
        nested = params["properties"]["filters"]
        self.assertFalse(nested["additionalProperties"])
        self.assertEqual(nested["required"], ["limit"])

    def test_make_deepseek_strict_tools_keeps_empty_tools(self) -> None:
        self.assertIsNone(make_deepseek_strict_tools(None))
        self.assertEqual(make_deepseek_strict_tools([]), [])


if __name__ == "__main__":
    unittest.main()
