"""Onboarding adapter interfaces and default prompt-based adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .install_rules import InstallChannelPromptRule, INSTALL_CHANNEL_PROMPT_RULES, apply_install_channel_prompt_rules


class ProviderOnboardingAdapter(Protocol):
    """Provider onboarding adapter protocol."""

    provider_name: str

    def collect_credentials(
        self,
        *,
        provider_cfg: dict[str, Any],
        input_fn: Callable[[str], str],
        secret_input_fn: Callable[[str], str] | None = None,
    ) -> None:
        """Collect provider credentials into provider config payload."""


class ChannelOnboardingAdapter(Protocol):
    """Channel onboarding adapter protocol."""

    channel_name: str

    def collect_credentials(
        self,
        *,
        channel_cfg: dict[str, Any],
        input_fn: Callable[[str], str],
        secret_input_fn: Callable[[str], str] | None = None,
    ) -> None:
        """Collect channel credentials into channel config payload."""


@dataclass(frozen=True)
class ApiKeyProviderOnboardingAdapter:
    """Default provider adapter that prompts for one API key."""

    provider_name: str
    prompt: str

    def collect_credentials(
        self,
        *,
        provider_cfg: dict[str, Any],
        input_fn: Callable[[str], str],
        secret_input_fn: Callable[[str], str] | None = None,
    ) -> None:
        if str(provider_cfg.get("apiKey", "")).strip():
            return
        reader = secret_input_fn or input_fn
        value = reader(self.prompt).strip()
        if value:
            provider_cfg["apiKey"] = value


@dataclass(frozen=True)
class PromptRuleChannelOnboardingAdapter:
    """Default channel adapter that applies prompt rules for one channel."""

    channel_name: str
    prompt_rules: tuple[InstallChannelPromptRule, ...]

    def collect_credentials(
        self,
        *,
        channel_cfg: dict[str, Any],
        input_fn: Callable[[str], str],
        secret_input_fn: Callable[[str], str] | None = None,
    ) -> None:
        apply_install_channel_prompt_rules(
            channels_cfg={self.channel_name: channel_cfg},
            enabled_channels=[self.channel_name],
            input_fn=input_fn,
            secret_input_fn=secret_input_fn,
            prompt_rules={self.channel_name: self.prompt_rules},
        )


_PROVIDER_ADAPTERS: dict[str, ProviderOnboardingAdapter] = {}
_CHANNEL_ADAPTERS: dict[str, ChannelOnboardingAdapter] = {
    name: PromptRuleChannelOnboardingAdapter(channel_name=name, prompt_rules=rules)
    for name, rules in INSTALL_CHANNEL_PROMPT_RULES.items()
}


def register_provider_onboarding_adapter(adapter: ProviderOnboardingAdapter) -> None:
    """Register or override one provider onboarding adapter."""

    _PROVIDER_ADAPTERS[adapter.provider_name] = adapter


def register_channel_onboarding_adapter(adapter: ChannelOnboardingAdapter) -> None:
    """Register or override one channel onboarding adapter."""

    _CHANNEL_ADAPTERS[adapter.channel_name] = adapter


def resolve_provider_onboarding_adapter(provider_name: str) -> ProviderOnboardingAdapter | None:
    """Resolve one provider onboarding adapter by provider name."""

    return _PROVIDER_ADAPTERS.get(provider_name)


def resolve_channel_onboarding_adapter(channel_name: str) -> ChannelOnboardingAdapter | None:
    """Resolve one channel onboarding adapter by channel name."""

    return _CHANNEL_ADAPTERS.get(channel_name)
