"""Tests for channel factory configuration logic."""

from __future__ import annotations

import os
import unittest

from sentientagent_v2.bus.queue import MessageBus
from sentientagent_v2.channels.factory import (
    build_channel_manager,
    parse_enabled_channels,
    validate_channel_setup,
)


class ChannelFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_backup = dict(os.environ)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_parse_enabled_channels_dedup(self) -> None:
        names = parse_enabled_channels("local,feishu,local")
        self.assertEqual(names, ["local", "feishu"])

    def test_parse_enabled_channels_empty_falls_back_to_local(self) -> None:
        names = parse_enabled_channels("")
        self.assertEqual(names, ["local"])

    def test_validate_reports_unknown(self) -> None:
        issues = validate_channel_setup(["unknown"])
        self.assertTrue(any("Unsupported channels" in item for item in issues))

    def test_validate_reports_known_but_unimplemented_channel(self) -> None:
        issues = validate_channel_setup(["telegram"])
        self.assertTrue(any("Missing TELEGRAM_BOT_TOKEN" in item for item in issues))
        self.assertFalse(any("Unsupported channels" in item for item in issues))

    def test_build_local_channel_manager(self) -> None:
        manager, local_channel = build_channel_manager(bus=MessageBus(), channel_names=["local"])
        self.assertIsNotNone(local_channel)
        self.assertIn("local", manager.channels)

    def test_build_manager_skips_unimplemented_channel(self) -> None:
        os.environ["TELEGRAM_BOT_TOKEN"] = "token-1"
        manager, local_channel = build_channel_manager(bus=MessageBus(), channel_names=["local", "telegram"])
        self.assertIsNotNone(local_channel)
        self.assertIn("local", manager.channels)
        self.assertIn("telegram", manager.channels)


if __name__ == "__main__":
    unittest.main()
