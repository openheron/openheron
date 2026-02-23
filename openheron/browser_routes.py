"""Browser route registration for openheron control service.

Iteration 1 introduces a route layer between the tool-facing API and browser
runtime so future adapters (Playwright/CDP/remote proxy) can plug in without
changing tool contracts.
"""

from __future__ import annotations

from typing import Any, Protocol

from .browser_runtime import BrowserRuntime, BrowserRuntimeError


class BrowserRouteRequest(Protocol):
    """Lightweight request protocol consumed by route handlers."""

    method: str
    path: str
    query: dict[str, Any]
    body: dict[str, Any]


class BrowserRouteResponse(Protocol):
    """Lightweight response protocol consumed by route handlers."""

    def status(self, code: int) -> "BrowserRouteResponse":
        """Set response status code."""

    def json(self, payload: Any) -> None:
        """Set JSON payload."""


class BrowserRouteRegistrar(Protocol):
    """Route registry protocol used by `register_browser_routes`."""

    def get(self, path: str, handler: Any) -> None:
        """Register GET route."""

    def post(self, path: str, handler: Any) -> None:
        """Register POST route."""


def _runtime_error_payload(exc: BrowserRuntimeError) -> dict[str, Any]:
    return {"ok": False, "error": str(exc), "status": exc.status}


def _handle_runtime_error(res: BrowserRouteResponse, exc: BrowserRuntimeError) -> None:
    res.status(exc.status).json(_runtime_error_payload(exc))


def register_browser_basic_routes(registrar: BrowserRouteRegistrar, runtime: BrowserRuntime) -> None:
    """Register browser basic routes (status/lifecycle/profile/tab list)."""

    def status_route(req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        res.json(runtime.status(profile=str(req.query.get("profile") or "").strip() or None))

    def start_route(req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        res.json(runtime.start(profile=str(req.query.get("profile") or "").strip() or None))

    def stop_route(req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        res.json(runtime.stop(profile=str(req.query.get("profile") or "").strip() or None))

    def profiles_route(_req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        res.json(runtime.profiles())

    def tabs_route(req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        res.json(runtime.tabs(profile=str(req.query.get("profile") or "").strip() or None))

    registrar.get("/", status_route)
    registrar.post("/start", start_route)
    registrar.post("/stop", stop_route)
    registrar.get("/profiles", profiles_route)
    registrar.get("/tabs", tabs_route)


def register_browser_agent_routes(registrar: BrowserRouteRegistrar, runtime: BrowserRuntime) -> None:
    """Register browser agent routes (open/navigate/snapshot/screenshot/upload/dialog/act)."""

    def open_route(req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        url = str(req.body.get("url") or "").strip()
        if not url:
            res.status(400).json({"ok": False, "error": "url is required"})
            return
        profile = str(req.query.get("profile") or "").strip() or None
        try:
            res.json(runtime.open_tab(url=url, profile=profile))
        except BrowserRuntimeError as exc:
            _handle_runtime_error(res, exc)

    def snapshot_route(req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        query = req.query
        target_id = str(query.get("targetId") or "").strip() or None
        snapshot_format = str(query.get("format") or "ai").strip().lower() or "ai"
        profile = str(query.get("profile") or "").strip() or None
        try:
            res.json(
                runtime.snapshot(
                    target_id=target_id,
                    snapshot_format=snapshot_format,
                    profile=profile,
                )
            )
        except BrowserRuntimeError as exc:
            _handle_runtime_error(res, exc)

    def navigate_route(req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        body = req.body
        url = str(body.get("url") or "").strip()
        if not url:
            res.status(400).json({"ok": False, "error": "url is required"})
            return
        target_id = str(body.get("targetId") or "").strip() or None
        profile = str(req.query.get("profile") or "").strip() or None
        try:
            res.json(runtime.navigate(url=url, target_id=target_id, profile=profile))
        except BrowserRuntimeError as exc:
            _handle_runtime_error(res, exc)

    def screenshot_route(req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        body = req.body
        target_id = str(body.get("targetId") or "").strip() or None
        image_type = str(body.get("type") or "png").strip().lower() or "png"
        out_path = str(body.get("path") or "").strip() or None
        profile = str(req.query.get("profile") or "").strip() or None
        try:
            res.json(
                runtime.screenshot(
                    target_id=target_id,
                    profile=profile,
                    image_type=image_type,
                    out_path=out_path,
                )
            )
        except BrowserRuntimeError as exc:
            _handle_runtime_error(res, exc)

    def upload_route(req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        body = req.body
        raw_paths = body.get("paths")
        paths = [str(item) for item in raw_paths] if isinstance(raw_paths, list) else []
        target_id = str(body.get("targetId") or "").strip() or None
        ref = str(body.get("ref") or "").strip() or None
        profile = str(req.query.get("profile") or "").strip() or None
        if not paths:
            res.status(400).json({"ok": False, "error": "paths are required"})
            return
        try:
            res.json(
                runtime.upload(
                    paths=paths,
                    target_id=target_id,
                    profile=profile,
                    ref=ref,
                )
            )
        except BrowserRuntimeError as exc:
            _handle_runtime_error(res, exc)

    def dialog_route(req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        body = req.body
        accept_raw = body.get("accept")
        if not isinstance(accept_raw, bool):
            res.status(400).json({"ok": False, "error": "accept is required and must be boolean"})
            return
        target_id = str(body.get("targetId") or "").strip() or None
        prompt_text = str(body.get("promptText") or "").strip() or None
        profile = str(req.query.get("profile") or "").strip() or None
        try:
            res.json(
                runtime.dialog(
                    accept=accept_raw,
                    target_id=target_id,
                    profile=profile,
                    prompt_text=prompt_text,
                )
            )
        except BrowserRuntimeError as exc:
            _handle_runtime_error(res, exc)

    def act_route(req: BrowserRouteRequest, res: BrowserRouteResponse) -> None:
        body = req.body
        request = body.get("request")
        if not isinstance(request, dict):
            # Compatibility path: accept flat /act payloads where action fields
            # are passed directly in request body.
            request = body
        if not isinstance(request, dict) or not str(request.get("kind") or "").strip():
            res.status(400).json({"ok": False, "error": "request.kind is required"})
            return
        target_id = str(body.get("targetId") or "").strip() or None
        profile = str(req.query.get("profile") or "").strip() or None
        try:
            res.json(runtime.act(request=request, target_id=target_id, profile=profile))
        except BrowserRuntimeError as exc:
            _handle_runtime_error(res, exc)

    registrar.post("/tabs/open", open_route)
    registrar.post("/navigate", navigate_route)
    registrar.get("/snapshot", snapshot_route)
    registrar.post("/screenshot", screenshot_route)
    registrar.post("/hooks/file-chooser", upload_route)
    registrar.post("/hooks/dialog", dialog_route)
    registrar.post("/act", act_route)


def register_browser_routes(registrar: BrowserRouteRegistrar, runtime: BrowserRuntime) -> None:
    """Register all browser routes for the control service."""

    register_browser_basic_routes(registrar, runtime)
    register_browser_agent_routes(registrar, runtime)
