"""Provider resolution helpers for sentientagent_v2 runtime."""

from __future__ import annotations

import importlib.util
import os
from typing import Any

DEFAULT_PROVIDER = "google"
DEFAULT_PROVIDER_MODELS = {
    "google": "gemini-3-flash-preview",
    "openai": "openai/gpt-4.1-mini",
    # Reserved for future runtime support.
    "openrouter": "openrouter/openai/gpt-4.1-mini",
}
SUPPORTED_PROVIDERS = frozenset({"google", "openai"})
PROVIDER_API_KEY_ENVS = {
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def normalize_provider_name(raw: str | None) -> str:
    """Normalize provider name from env/config."""
    return (raw or "").strip().lower() or DEFAULT_PROVIDER


def default_model_for_provider(provider: str) -> str:
    """Return provider-specific default model name."""
    return DEFAULT_PROVIDER_MODELS.get(provider, DEFAULT_PROVIDER_MODELS[DEFAULT_PROVIDER])


def normalize_model_name(provider: str, raw_model: str | None) -> str:
    """Normalize provider model value with safe defaults."""
    model = (raw_model or "").strip() or default_model_for_provider(provider)
    if provider == "openai" and "/" not in model:
        return f"openai/{model}"
    return model


def provider_api_key_env(provider: str) -> str | None:
    """Return the API key env var used by a provider."""
    return PROVIDER_API_KEY_ENVS.get(provider)


def validate_provider_runtime(provider: str) -> str | None:
    """Validate whether provider runtime dependencies are available."""
    if provider not in SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        return f"Provider '{provider}' is not supported by runtime yet (supported: {supported})."
    if provider == "openai" and importlib.util.find_spec("litellm") is None:
        return "OpenAI provider requires `litellm`. Install with: pip install -e '.[openai]'"
    return None


def build_adk_model_from_env() -> Any:
    """Build ADK model object/string based on selected provider."""
    provider = normalize_provider_name(os.getenv("SENTIENTAGENT_V2_PROVIDER"))
    model_name = normalize_model_name(provider, os.getenv("SENTIENTAGENT_V2_MODEL"))
    issue = validate_provider_runtime(provider)
    if issue:
        raise RuntimeError(issue)

    if provider == "google":
        return model_name

    if provider == "openai":
        from google.adk.models.lite_llm import LiteLlm

        return LiteLlm(model=model_name)

    raise RuntimeError(f"Unsupported provider '{provider}'.")
