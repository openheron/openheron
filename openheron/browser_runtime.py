"""Minimal browser runtime abstraction for openheron native browser tool.

This module provides an in-memory runtime used by Iteration 0 so the browser
tool has a deterministic, testable execution path before wiring real
Playwright/CDP backends in later iterations.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import os
from typing import Any, Protocol
from urllib.parse import urlparse
import uuid


_SUPPORTED_SCHEMES = {"http", "https", "about"}


@dataclass(slots=True)
class BrowserTab:
    """A lightweight tab record returned by the browser runtime."""

    target_id: str
    url: str
    title: str
    tab_type: str = "page"


class BrowserRuntimeError(RuntimeError):
    """Browser runtime error with an HTTP-like status code."""

    def __init__(self, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


class BrowserRuntime(Protocol):
    """Protocol for browser runtime backends."""

    def status(self, *, profile: str | None = None) -> dict[str, Any]:
        """Return browser runtime status."""

    def start(self, *, profile: str | None = None) -> dict[str, Any]:
        """Start browser runtime."""

    def stop(self, *, profile: str | None = None) -> dict[str, Any]:
        """Stop browser runtime."""

    def profiles(self) -> dict[str, Any]:
        """Return available browser profiles."""

    def tabs(self, *, profile: str | None = None) -> dict[str, Any]:
        """Return opened tabs."""

    def open_tab(self, *, url: str, profile: str | None = None) -> dict[str, Any]:
        """Open a new tab."""

    def navigate(
        self,
        *,
        url: str,
        target_id: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        """Navigate an existing tab to a URL."""

    def snapshot(
        self,
        *,
        target_id: str | None = None,
        snapshot_format: str = "ai",
        profile: str | None = None,
    ) -> dict[str, Any]:
        """Return snapshot for one tab."""

    def act(
        self,
        *,
        request: dict[str, Any],
        target_id: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        """Run one browser action on the selected tab."""

    def screenshot(
        self,
        *,
        target_id: str | None = None,
        profile: str | None = None,
        image_type: str = "png",
        out_path: str | None = None,
    ) -> dict[str, Any]:
        """Capture tab screenshot."""

    def upload(
        self,
        *,
        paths: list[str],
        target_id: str | None = None,
        profile: str | None = None,
        ref: str | None = None,
    ) -> dict[str, Any]:
        """Upload files to the current page context."""

    def dialog(
        self,
        *,
        accept: bool,
        target_id: str | None = None,
        profile: str | None = None,
        prompt_text: str | None = None,
    ) -> dict[str, Any]:
        """Arm dialog handling for the current page."""


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in _SUPPORTED_SCHEMES:
        raise BrowserRuntimeError("target_url must use http/https/about scheme")
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise BrowserRuntimeError("target_url must include host for http/https")


class InMemoryBrowserRuntime:
    """In-memory browser runtime for Iteration 0.

    The runtime emulates OpenClaw-like action flow (`open -> snapshot -> act`)
    while keeping behavior deterministic for unit tests.
    """

    def __init__(self) -> None:
        self._running = False
        self._tabs: list[BrowserTab] = []
        self._last_target_id: str | None = None

    def status(self, *, profile: str | None = None) -> dict[str, Any]:
        return {
            "enabled": True,
            "running": self._running,
            "profile": profile or "openheron",
            "tabCount": len(self._tabs),
            "lastTargetId": self._last_target_id,
        }

    def start(self, *, profile: str | None = None) -> dict[str, Any]:
        self._running = True
        return self.status(profile=profile)

    def stop(self, *, profile: str | None = None) -> dict[str, Any]:
        self._running = False
        self._tabs = []
        self._last_target_id = None
        return self.status(profile=profile)

    def profiles(self) -> dict[str, Any]:
        return {
            "profiles": [
                {
                    "name": "openheron",
                    "driver": "memory",
                    "description": "Iteration 0 in-memory browser profile",
                }
            ]
        }

    def tabs(self, *, profile: str | None = None) -> dict[str, Any]:
        return {
            "running": self._running,
            "profile": profile or "openheron",
            "tabs": [
                {
                    "targetId": tab.target_id,
                    "url": tab.url,
                    "title": tab.title,
                    "type": tab.tab_type,
                }
                for tab in self._tabs
            ],
        }

    def open_tab(self, *, url: str, profile: str | None = None) -> dict[str, Any]:
        if not self._running:
            raise BrowserRuntimeError("browser is not running; call action=start first", status=409)
        _validate_url(url)
        tab = BrowserTab(
            target_id=f"tab-{uuid.uuid4().hex[:8]}",
            url=url,
            title=f"OpenHeron: {url}",
        )
        self._tabs.append(tab)
        self._last_target_id = tab.target_id
        return {
            "ok": True,
            "profile": profile or "openheron",
            "targetId": tab.target_id,
            "url": tab.url,
            "title": tab.title,
        }

    def snapshot(
        self,
        *,
        target_id: str | None = None,
        snapshot_format: str = "ai",
        profile: str | None = None,
    ) -> dict[str, Any]:
        tab = self._resolve_tab(target_id)
        if snapshot_format not in {"ai", "aria"}:
            raise BrowserRuntimeError("snapshot_format must be 'ai' or 'aria'")
        self._last_target_id = tab.target_id
        if snapshot_format == "aria":
            return {
                "ok": True,
                "format": "aria",
                "profile": profile or "openheron",
                "targetId": tab.target_id,
                "url": tab.url,
                "nodes": [
                    {"ref": "ax1", "role": "document", "name": tab.title},
                    {"ref": "ax2", "role": "textbox", "name": "Search"},
                ],
            }
        return {
            "ok": True,
            "format": "ai",
            "profile": profile or "openheron",
            "targetId": tab.target_id,
            "url": tab.url,
            "snapshot": f"URL: {tab.url}\nTitle: {tab.title}\nInteractive refs: e1(button), e2(input)",
            "refs": {
                "e1": {"role": "button", "name": "Submit"},
                "e2": {"role": "textbox", "name": "Input"},
            },
        }

    def navigate(
        self,
        *,
        url: str,
        target_id: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        tab = self._resolve_tab(target_id)
        _validate_url(url)
        tab.url = url
        tab.title = f"OpenHeron: {url}"
        self._last_target_id = tab.target_id
        return {
            "ok": True,
            "profile": profile or "openheron",
            "targetId": tab.target_id,
            "url": tab.url,
            "title": tab.title,
        }

    def act(
        self,
        *,
        request: dict[str, Any],
        target_id: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        tab = self._resolve_tab(target_id)
        kind = str(request.get("kind", "")).strip()
        if not kind:
            raise BrowserRuntimeError("request.kind is required")
        if kind not in {"click", "type", "press", "wait", "close"}:
            raise BrowserRuntimeError(f"unsupported act kind: {kind}")
        selector = str(request.get("selector", "")).strip()
        ref = str(request.get("ref", "")).strip()
        if kind in {"click", "type"} and not (selector or ref):
            raise BrowserRuntimeError("request.selector or request.ref is required for click/type")
        if kind == "type" and not isinstance(request.get("text"), str):
            raise BrowserRuntimeError("request.text is required for type")
        if kind == "press" and not str(request.get("key", "")).strip():
            raise BrowserRuntimeError("request.key is required for press")

        if kind == "close":
            self._tabs = [entry for entry in self._tabs if entry.target_id != tab.target_id]
            self._last_target_id = self._tabs[-1].target_id if self._tabs else None
            return {
                "ok": True,
                "profile": profile or "openheron",
                "targetId": tab.target_id,
                "closed": True,
            }
        self._last_target_id = tab.target_id
        return {
            "ok": True,
            "profile": profile or "openheron",
            "targetId": tab.target_id,
            "url": tab.url,
            "kind": kind,
        }

    def screenshot(
        self,
        *,
        target_id: str | None = None,
        profile: str | None = None,
        image_type: str = "png",
        out_path: str | None = None,
    ) -> dict[str, Any]:
        tab = self._resolve_tab(target_id)
        fmt = image_type.strip().lower()
        if fmt not in {"png", "jpeg"}:
            raise BrowserRuntimeError("image_type must be 'png' or 'jpeg'")
        # 1x1 transparent PNG placeholder so contract is stable in memory mode.
        png_base64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y1koS8AAAAASUVORK5CYII="
        )
        data = png_base64 if fmt == "png" else png_base64
        content_type = "image/png" if fmt == "png" else "image/jpeg"
        binary = base64.b64decode(data)
        saved_path: str | None = None
        if out_path and out_path.strip():
            target_path = os.path.abspath(out_path.strip())
            dirpath = os.path.dirname(target_path) or "."
            os.makedirs(dirpath, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(binary)
            saved_path = target_path
        self._last_target_id = tab.target_id
        return {
            "ok": True,
            "profile": profile or "openheron",
            "targetId": tab.target_id,
            "url": tab.url,
            "type": fmt,
            "contentType": content_type,
            "imageBase64": data,
            "bytes": len(binary),
            "path": saved_path,
        }

    def upload(
        self,
        *,
        paths: list[str],
        target_id: str | None = None,
        profile: str | None = None,
        ref: str | None = None,
    ) -> dict[str, Any]:
        tab = self._resolve_tab(target_id)
        if not paths:
            raise BrowserRuntimeError("paths are required for upload")
        resolved: list[str] = []
        for raw in paths:
            path_value = str(raw).strip()
            if not path_value:
                continue
            if not os.path.isfile(path_value):
                raise BrowserRuntimeError(f"upload file not found: {path_value}", status=404)
            resolved.append(path_value)
        if not resolved:
            raise BrowserRuntimeError("paths are required for upload")
        self._last_target_id = tab.target_id
        return {
            "ok": True,
            "profile": profile or "openheron",
            "targetId": tab.target_id,
            "uploadedPaths": resolved,
            "ref": ref or None,
        }

    def dialog(
        self,
        *,
        accept: bool,
        target_id: str | None = None,
        profile: str | None = None,
        prompt_text: str | None = None,
    ) -> dict[str, Any]:
        tab = self._resolve_tab(target_id)
        self._last_target_id = tab.target_id
        return {
            "ok": True,
            "profile": profile or "openheron",
            "targetId": tab.target_id,
            "accept": bool(accept),
            "promptText": prompt_text or None,
            "armed": True,
        }

    def _resolve_tab(self, target_id: str | None) -> BrowserTab:
        if not self._running:
            raise BrowserRuntimeError("browser is not running; call action=start first", status=409)
        if not self._tabs:
            raise BrowserRuntimeError("no tabs available; call action=open first", status=404)
        if target_id:
            for tab in self._tabs:
                if tab.target_id == target_id:
                    return tab
            raise BrowserRuntimeError("tab not found", status=404)
        if self._last_target_id:
            for tab in self._tabs:
                if tab.target_id == self._last_target_id:
                    return tab
        return self._tabs[-1]


_runtime: BrowserRuntime | None = None


def _create_playwright_runtime() -> BrowserRuntime:
    """Create Playwright runtime lazily to avoid hard dependency at import time."""

    from .browser_playwright_runtime import PlaywrightBrowserRuntime

    return PlaywrightBrowserRuntime()


def _create_runtime_from_env() -> BrowserRuntime:
    """Resolve runtime implementation from environment with safe fallback.

    `OPENHERON_BROWSER_RUNTIME=playwright` enables Playwright backend. If
    Playwright backend cannot be created, we gracefully fallback to in-memory.
    """

    mode = os.getenv("OPENHERON_BROWSER_RUNTIME", "").strip().lower()
    if mode == "playwright":
        try:
            return _create_playwright_runtime()
        except Exception:
            return InMemoryBrowserRuntime()
    return InMemoryBrowserRuntime()


def get_browser_runtime() -> BrowserRuntime:
    """Return the active browser runtime."""

    global _runtime
    if _runtime is None:
        _runtime = _create_runtime_from_env()
    return _runtime


def configure_browser_runtime(runtime: BrowserRuntime | None) -> None:
    """Set browser runtime for tests or adapters.

    Passing ``None`` resets to the default in-memory runtime.
    """

    global _runtime
    _runtime = runtime if runtime is not None else _create_runtime_from_env()
    # Keep dispatcher routes bound to the newest runtime instance in tests.
    try:
        from .browser_service import reset_browser_control_service

        reset_browser_control_service()
    except Exception:
        # Avoid hard dependency cycles during early imports.
        pass
