"""Tests for sentientagent_v2 core tools."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from sentientagent_v2.tools import (
    cron,
    edit_file,
    exec_command,
    list_dir,
    message,
    read_file,
    web_fetch,
    write_file,
)


class ToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_backup = dict(os.environ)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_file_tools_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["SENTIENTAGENT_V2_WORKSPACE"] = tmp
            out = write_file("tmp/demo.txt", "hello world")
            self.assertIn("Successfully wrote", out)
            content = read_file("tmp/demo.txt")
            self.assertEqual(content, "hello world")
            edited = edit_file("tmp/demo.txt", "world", "adk")
            self.assertIn("Successfully edited", edited)
            self.assertEqual(read_file("tmp/demo.txt"), "hello adk")

    def test_list_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["SENTIENTAGENT_V2_WORKSPACE"] = tmp
            Path(tmp, "a").mkdir()
            Path(tmp, "b.txt").write_text("x", encoding="utf-8")
            listing = list_dir(".")
            self.assertIn("[D] a", listing)
            self.assertIn("[F] b.txt", listing)

    def test_exec_tool(self) -> None:
        result = exec_command("echo hello")
        self.assertIn("hello", result)

    def test_message_tool_writes_outbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["SENTIENTAGENT_V2_WORKSPACE"] = tmp
            response = message("hi", channel="local", chat_id="u1")
            self.assertIn("Message recorded", response)
            outbox = Path(tmp) / "messages" / "outbox.log"
            self.assertTrue(outbox.exists())

    def test_cron_tool_add_list_remove(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["SENTIENTAGENT_V2_WORKSPACE"] = tmp
            create = cron(action="add", message="remind me", every_seconds=30)
            self.assertIn("Created job", create)

            listing = cron(action="list")
            self.assertIn("Scheduled jobs", listing)

            job_id = create.split("(id: ", 1)[1].rstrip(")")
            removed = cron(action="remove", job_id=job_id)
            self.assertIn("Removed job", removed)

    def test_web_fetch_rejects_invalid_url(self) -> None:
        payload = json.loads(web_fetch("file:///tmp/test.txt"))
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
