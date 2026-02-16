"""Tests for sentientagent_v2 CLI behavior."""

from __future__ import annotations

import types as pytypes
import unittest
from pathlib import Path
from unittest.mock import patch


class CLITests(unittest.TestCase):
    def test_message_mode_dispatch(self) -> None:
        from sentientagent_v2 import cli

        with patch.object(cli, "_cmd_message", return_value=0) as mocked:
            with self.assertRaises(SystemExit) as ctx:
                cli.main(["-m", "hello"])
            self.assertEqual(ctx.exception.code, 0)
            mocked.assert_called_once()

    def test_script_entrypoint_accepts_m(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        script_path = project_root / "sentientagent_v2-cli"
        self.assertTrue(script_path.exists())

    def test_cmd_message_collects_final_text(self) -> None:
        from sentientagent_v2 import cli

        fake_event_1 = pytypes.SimpleNamespace(content=pytypes.SimpleNamespace(parts=[]))
        fake_event_2 = pytypes.SimpleNamespace(
            content=pytypes.SimpleNamespace(parts=[pytypes.SimpleNamespace(text="final answer")])
        )

        class _FakeSessionService:
            async def create_session(self, **kwargs):
                return None

        class _FakeRunner:
            def __init__(self, **kwargs):
                pass

            async def run_async(self, **kwargs):
                yield fake_event_1
                yield fake_event_2

        fake_agent = pytypes.SimpleNamespace(name="sentientagent_v2")
        fake_agent_module = pytypes.SimpleNamespace(root_agent=fake_agent)

        with patch.dict("sys.modules", {"sentientagent_v2.agent": fake_agent_module}):
            with patch("sentientagent_v2.cli.InMemorySessionService", _FakeSessionService):
                with patch("sentientagent_v2.cli.Runner", _FakeRunner):
                    with patch("builtins.print") as mocked_print:
                        code = cli._cmd_message("hello", user_id="u1", session_id="s1")

        self.assertEqual(code, 0)
        mocked_print.assert_called_with("final answer")


if __name__ == "__main__":
    unittest.main()
