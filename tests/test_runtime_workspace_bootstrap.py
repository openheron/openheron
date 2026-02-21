"""Tests for workspace bootstrap prompt injection."""

from __future__ import annotations

import asyncio
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from openheron.runtime.workspace_bootstrap import (
    before_model_workspace_bootstrap_callback,
    load_workspace_bootstrap_sections,
)


class WorkspaceBootstrapTests(unittest.TestCase):
    def test_loader_reads_agents_soul_user_in_fixed_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("agents-rules", encoding="utf-8")
            (root / "SOUL.md").write_text("soul-tone", encoding="utf-8")
            (root / "USER.md").write_text("user-profile", encoding="utf-8")
            (root / "TOOLS.md").write_text("tools-not-supported-yet", encoding="utf-8")

            sections = load_workspace_bootstrap_sections(root)

        self.assertEqual([item.name for item in sections], ["AGENTS.md", "SOUL.md", "USER.md"])
        merged = "\n".join(item.content for item in sections)
        self.assertIn("agents-rules", merged)
        self.assertIn("soul-tone", merged)
        self.assertIn("user-profile", merged)
        self.assertNotIn("tools-not-supported-yet", merged)

    def test_callback_prepends_workspace_context_to_system_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("follow local agent rules", encoding="utf-8")
            (root / "SOUL.md").write_text("keep a concise tone", encoding="utf-8")
            (root / "USER.md").write_text("user prefers chinese", encoding="utf-8")
            (root / "TOOLS.md").write_text("should not be injected", encoding="utf-8")

            llm_request = types.SimpleNamespace(
                config=types.SimpleNamespace(system_instruction="base-system-instruction"),
            )

            with patch.dict(os.environ, {"OPENHERON_WORKSPACE": str(root)}, clear=False):
                asyncio.run(before_model_workspace_bootstrap_callback(types.SimpleNamespace(), llm_request))

        system_instruction = llm_request.config.system_instruction
        self.assertIn("Workspace Context (injected by openheron)", system_instruction)
        self.assertIn("## AGENTS.md", system_instruction)
        self.assertIn("## SOUL.md", system_instruction)
        self.assertIn("## USER.md", system_instruction)
        self.assertIn("follow local agent rules", system_instruction)
        self.assertIn("keep a concise tone", system_instruction)
        self.assertIn("user prefers chinese", system_instruction)
        self.assertNotIn("should not be injected", system_instruction)
        self.assertLess(
            system_instruction.index("Workspace Context (injected by openheron)"),
            system_instruction.index("base-system-instruction"),
        )

    def test_callback_keeps_instruction_when_no_supported_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            llm_request = types.SimpleNamespace(
                config=types.SimpleNamespace(system_instruction="base-system-instruction"),
            )
            with patch.dict(os.environ, {"OPENHERON_WORKSPACE": str(root)}, clear=False):
                asyncio.run(before_model_workspace_bootstrap_callback(types.SimpleNamespace(), llm_request))

        self.assertEqual(llm_request.config.system_instruction, "base-system-instruction")

    def test_callback_accepts_adk_keyword_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("agents-rules", encoding="utf-8")
            llm_request = types.SimpleNamespace(
                config=types.SimpleNamespace(system_instruction="base-system-instruction"),
            )
            with patch.dict(os.environ, {"OPENHERON_WORKSPACE": str(root)}, clear=False):
                asyncio.run(
                    before_model_workspace_bootstrap_callback(
                        callback_context=types.SimpleNamespace(),
                        llm_request=llm_request,
                    )
                )

        self.assertIn("Workspace Context (injected by openheron)", llm_request.config.system_instruction)


if __name__ == "__main__":
    unittest.main()
