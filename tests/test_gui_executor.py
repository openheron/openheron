"""Tests for GUI grounding executor."""

from __future__ import annotations

import unittest
import unittest.mock

from openheron.gui_executor import CapturedScreen, GroundingExecutor, PyAutoGuiRuntime


class _FakeRuntime:
    def __init__(self, captures: list[str] | None = None) -> None:
        self.calls: list[dict] = []
        self._captures = captures[:] if captures else []
        self._capture_index = 0

    def capture(self) -> CapturedScreen:
        index = self._capture_index
        self._capture_index += 1
        base64_png = (
            self._captures[index]
            if index < len(self._captures)
            else f"ZmFrZS0{index}"
        )
        return CapturedScreen(
            base64_png=base64_png,
            width=1920,
            height=1080,
            path=f"/tmp/fake-{index}.png",
        )

    def perform(self, arguments: dict) -> None:
        self.calls.append(arguments)


class _FakeCompletions:
    def __init__(self, content: str | list[str]) -> None:
        if isinstance(content, list):
            self._contents = content[:]
        else:
            self._contents = [content]
        self._index = 0

    def create(self, **_: object) -> object:
        content = self._contents[min(self._index, len(self._contents) - 1)]
        self._index += 1
        message = type("Message", (), {"content": content})()
        choice = type("Choice", (), {"message": message})()
        return type("Completion", (), {"choices": [choice]})()


class _FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = type(
            "Chat",
            (),
            {"completions": _FakeCompletions(content)},
        )()


class GuiExecutorTests(unittest.TestCase):
    def test_executor_runs_with_tool_call_block(self) -> None:
        runtime = _FakeRuntime()
        client = _FakeClient(
            '<tool_call>{"name":"computer_use","arguments":{"action":"left_click","coordinate":[500,500]}}</tool_call>'
        )

        executor = GroundingExecutor(
            model="test-model",
            api_key="test-key",
            runtime=runtime,
            client=client,
        )
        result = executor.run("click center")

        self.assertTrue(result["ok"])
        self.assertEqual(result["arguments"]["action"], "left_click")
        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(runtime.calls[0]["coordinate"], [500, 500])

    def test_executor_respects_dry_run(self) -> None:
        runtime = _FakeRuntime()
        client = _FakeClient('{"action":"wait","time":1}')
        executor = GroundingExecutor(
            model="test-model",
            api_key="test-key",
            runtime=runtime,
            client=client,
        )

        result = executor.run("wait", dry_run=True)

        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertEqual(runtime.calls, [])

    def test_runtime_blocks_dangerous_key_chord(self) -> None:
        class _FakeAutoGui:
            class _Size:
                width = 1920
                height = 1080

            def size(self):
                return self._Size()

        runtime = PyAutoGuiRuntime(
            pyautogui_module=_FakeAutoGui(),
            pyperclip_module=object(),
            allow_dangerous_keys=False,
        )

        with self.assertRaises(ValueError):
            runtime.perform({"action": "key", "keys": ["command", "q"]})

    def test_runtime_caps_wait_seconds(self) -> None:
        class _FakeAutoGui:
            class _Size:
                width = 1920
                height = 1080

            def size(self):
                return self._Size()

        runtime = PyAutoGuiRuntime(
            pyautogui_module=_FakeAutoGui(),
            pyperclip_module=object(),
            max_wait_seconds=0.1,
        )

        with unittest.mock.patch("openheron.gui_executor.time.sleep") as mocked_sleep:
            runtime.perform({"action": "wait", "time": 8})
        mocked_sleep.assert_called_once_with(0.1)

    def test_runtime_blocks_action_by_blocklist(self) -> None:
        class _FakeAutoGui:
            class _Size:
                width = 1920
                height = 1080

            def size(self):
                return self._Size()

        runtime = PyAutoGuiRuntime(
            pyautogui_module=_FakeAutoGui(),
            pyperclip_module=object(),
            blocked_actions={"scroll"},
        )

        with self.assertRaises(ValueError):
            runtime.perform({"action": "scroll", "pixels": -100})

    def test_runtime_blocks_action_not_in_allowlist(self) -> None:
        class _FakeAutoGui:
            class _Size:
                width = 1920
                height = 1080

            def size(self):
                return self._Size()

        runtime = PyAutoGuiRuntime(
            pyautogui_module=_FakeAutoGui(),
            pyperclip_module=object(),
            allowed_actions={"wait"},
        )

        with self.assertRaises(ValueError):
            runtime.perform({"action": "left_click", "coordinate": [10, 10]})

    def test_executor_retries_parse_then_succeeds(self) -> None:
        runtime = _FakeRuntime()
        client = _FakeClient(
            [
                "not-json",
                '{"name":"computer_use","arguments":{"action":"wait","time":1}}',
            ]
        )
        executor = GroundingExecutor(
            model="test-model",
            api_key="test-key",
            runtime=runtime,
            client=client,
            max_parse_retries=1,
        )

        result = executor.run("wait")

        self.assertTrue(result["ok"])
        self.assertEqual(result["arguments"]["action"], "wait")
        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(result["retries_used"], 0)

    def test_executor_parse_retry_exhausted(self) -> None:
        runtime = _FakeRuntime()
        client = _FakeClient(["bad-output", "still-bad"])
        executor = GroundingExecutor(
            model="test-model",
            api_key="test-key",
            runtime=runtime,
            client=client,
            max_parse_retries=1,
        )

        with self.assertRaises(ValueError):
            executor.run("click")

    def test_executor_retries_when_screen_unchanged(self) -> None:
        runtime = _FakeRuntime(captures=["same", "same", "before-2", "after-2"])
        client = _FakeClient(
            [
                '{"name":"computer_use","arguments":{"action":"left_click","coordinate":[500,500]}}',
                '{"name":"computer_use","arguments":{"action":"left_click","coordinate":[500,500]}}',
            ]
        )
        executor = GroundingExecutor(
            model="test-model",
            api_key="test-key",
            runtime=runtime,
            client=client,
            max_action_retries=1,
            verify_screen_change=True,
        )

        result = executor.run("click once")

        self.assertTrue(result["ok"])
        self.assertTrue(result["screen_changed"])
        self.assertEqual(result["retries_used"], 1)
        self.assertEqual(len(runtime.calls), 2)


if __name__ == "__main__":
    unittest.main()
