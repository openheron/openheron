"""Tests for browser runtime selection/fallback logic."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from openheron.browser_runtime import (
    InMemoryBrowserRuntime,
    configure_browser_runtime,
    get_browser_runtime,
)


class BrowserRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_backup = dict(os.environ)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_backup)
        configure_browser_runtime(InMemoryBrowserRuntime())

    def test_default_runtime_is_in_memory(self) -> None:
        os.environ.pop("OPENHERON_BROWSER_RUNTIME", None)
        configure_browser_runtime(None)
        runtime = get_browser_runtime()
        self.assertIsInstance(runtime, InMemoryBrowserRuntime)

    def test_playwright_mode_falls_back_to_memory_when_adapter_fails(self) -> None:
        os.environ["OPENHERON_BROWSER_RUNTIME"] = "playwright"
        with patch("openheron.browser_runtime._create_playwright_runtime", side_effect=RuntimeError("boom")):
            configure_browser_runtime(None)
            runtime = get_browser_runtime()
        self.assertIsInstance(runtime, InMemoryBrowserRuntime)

    def test_playwright_mode_uses_adapter_when_available(self) -> None:
        os.environ["OPENHERON_BROWSER_RUNTIME"] = "playwright"
        sentinel = InMemoryBrowserRuntime()
        with patch("openheron.browser_runtime._create_playwright_runtime", return_value=sentinel):
            configure_browser_runtime(None)
            runtime = get_browser_runtime()
        self.assertIs(runtime, sentinel)


if __name__ == "__main__":
    unittest.main()
