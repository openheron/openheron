"""Channel registry metadata for factory/config alignment.

This module centralizes channel names and their bootstrap behavior:
- Which channels are recognized by config/CLI parsing.
- Which channels have runtime adapters implemented today.
- Which setup validations should run before gateway startup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from ..bus.queue import MessageBus
from .base import BaseChannel
from .feishu import FEISHU_AVAILABLE, FeishuChannel
from .local import LocalChannel
from .telegram import TelegramChannel


LocalWriter = Callable[[str], None] | None
ChannelBuilder = Callable[[MessageBus, LocalWriter], BaseChannel | None]
ChannelValidator = Callable[[], list[str]]


@dataclass(frozen=True, slots=True)
class ChannelSpec:
    """Static metadata for one channel type."""

    name: str
    build: ChannelBuilder
    validate_setup: ChannelValidator


def _build_local(bus: MessageBus, local_writer: LocalWriter) -> BaseChannel:
    return LocalChannel(bus=bus, writer=local_writer)


def _validate_local() -> list[str]:
    return []


def _build_feishu(bus: MessageBus, _local_writer: LocalWriter) -> BaseChannel:
    allow_from = [item.strip() for item in os.getenv("FEISHU_ALLOW_FROM", "").split(",") if item.strip()]
    return FeishuChannel(
        bus=bus,
        app_id=os.getenv("FEISHU_APP_ID", "").strip(),
        app_secret=os.getenv("FEISHU_APP_SECRET", "").strip(),
        encrypt_key=os.getenv("FEISHU_ENCRYPT_KEY", "").strip(),
        verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN", "").strip(),
        allow_from=allow_from,
    )


def _validate_feishu() -> list[str]:
    issues: list[str] = []
    if not FEISHU_AVAILABLE:
        issues.append("Feishu channel requires `lark-oapi` (pip install lark-oapi).")
    if not os.getenv("FEISHU_APP_ID", "").strip():
        issues.append("Missing FEISHU_APP_ID for feishu channel.")
    if not os.getenv("FEISHU_APP_SECRET", "").strip():
        issues.append("Missing FEISHU_APP_SECRET for feishu channel.")
    return issues


def _build_telegram(bus: MessageBus, _local_writer: LocalWriter) -> BaseChannel:
    allow_from = [item.strip() for item in os.getenv("TELEGRAM_ALLOW_FROM", "").split(",") if item.strip()]
    return TelegramChannel(
        bus=bus,
        token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        allow_from=allow_from,
        proxy=os.getenv("TELEGRAM_PROXY", "").strip(),
    )


def _validate_telegram() -> list[str]:
    if os.getenv("TELEGRAM_BOT_TOKEN", "").strip():
        return []
    return ["Missing TELEGRAM_BOT_TOKEN for telegram channel."]


def _build_not_implemented(_bus: MessageBus, _local_writer: LocalWriter) -> None:
    # Channel is known by configuration but has no runtime adapter yet.
    return None


def _validate_not_implemented(name: str) -> ChannelValidator:
    def _inner() -> list[str]:
        return [f"Channel '{name}' is recognized but not implemented yet in sentientagent_v2."]

    return _inner


CHANNEL_ORDER: tuple[str, ...] = (
    "local",
    "feishu",
    "telegram",
    "whatsapp",
    "discord",
    "mochat",
    "dingtalk",
    "email",
    "slack",
    "qq",
)


def _make_registry() -> dict[str, ChannelSpec]:
    specs: dict[str, ChannelSpec] = {
        "local": ChannelSpec(
            name="local",
            build=_build_local,
            validate_setup=_validate_local,
        ),
        "feishu": ChannelSpec(
            name="feishu",
            build=_build_feishu,
            validate_setup=_validate_feishu,
        ),
        "telegram": ChannelSpec(
            name="telegram",
            build=_build_telegram,
            validate_setup=_validate_telegram,
        ),
    }

    for name in CHANNEL_ORDER:
        if name in specs:
            continue
        specs[name] = ChannelSpec(
            name=name,
            build=_build_not_implemented,
            validate_setup=_validate_not_implemented(name),
        )
    return specs


CHANNEL_SPECS: dict[str, ChannelSpec] = _make_registry()


def known_channel_names() -> list[str]:
    """Return all recognized channel names in stable display order."""
    return [name for name in CHANNEL_ORDER if name in CHANNEL_SPECS]


def get_channel_spec(name: str) -> ChannelSpec | None:
    """Return channel spec by name."""
    return CHANNEL_SPECS.get(name)
