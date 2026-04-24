"""Tests for shared memory text extraction helpers."""

from __future__ import annotations

import types as pytypes
import unittest

from openppx.runtime.memory_shared import content_text_lines


class RuntimeMemorySharedTests(unittest.TestCase):
    def test_content_text_lines_skips_thought_parts(self) -> None:
        content = pytypes.SimpleNamespace(
            parts=[
                pytypes.SimpleNamespace(text="reasoning", thought=True),
                pytypes.SimpleNamespace(text="answer", thought=False),
            ]
        )

        self.assertEqual(content_text_lines(content), ["answer"])

    def test_content_text_lines_skips_mapping_thought_parts(self) -> None:
        content = {"parts": [{"text": "reasoning", "thought": True}, {"text": "answer"}]}

        self.assertEqual(content_text_lines(content), ["answer"])


if __name__ == "__main__":
    unittest.main()
