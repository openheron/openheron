"""Tests for routing capability metadata declarations."""

from __future__ import annotations

import unittest

from openheron.runtime.route_capabilities import (
    channel_supports_scope_metadata,
    describe_scope_capabilities,
    get_scope_capability,
    list_scope_metadata_supported_channels,
)


class RouteCapabilitiesTests(unittest.TestCase):
    def test_channel_supports_scope_metadata(self) -> None:
        self.assertTrue(channel_supports_scope_metadata("discord"))
        self.assertTrue(channel_supports_scope_metadata("feishu"))
        self.assertTrue(channel_supports_scope_metadata("DISCORD"))
        self.assertFalse(channel_supports_scope_metadata("telegram"))
        self.assertIn("discord", list_scope_metadata_supported_channels())
        self.assertIn("feishu", list_scope_metadata_supported_channels())
        self.assertEqual(get_scope_capability("telegram").level, "unsupported")
        self.assertIn("protocol model", get_scope_capability("telegram").reason)
        described = describe_scope_capabilities()
        self.assertIn("discord", described)
        self.assertIn("level", described["discord"])


if __name__ == "__main__":
    unittest.main()
