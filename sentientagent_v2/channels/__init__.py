"""Channel interfaces and adapters."""

from .base import BaseChannel
from .factory import build_channel_manager, parse_enabled_channels, validate_channel_setup
from .feishu import FeishuChannel
from .local import LocalChannel
from .manager import ChannelManager
from .telegram import TelegramChannel

__all__ = [
    "BaseChannel",
    "ChannelManager",
    "FeishuChannel",
    "LocalChannel",
    "TelegramChannel",
    "build_channel_manager",
    "parse_enabled_channels",
    "validate_channel_setup",
]
