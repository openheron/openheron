#!/usr/bin/env python3
"""Deterministic local smoke test for multi-agent isolation.

This script validates core v1 behavior without external channels:
1. channel+accountId routing splits traffic across agents.
2. session ids remain agent-scoped.
3. heartbeat snapshots are persisted per agent.
4. route-stats snapshots are persisted per agent.
5. agent bootstrap files are loaded from per-agent bootstrap dirs.

Usage:
  python scripts/multi_agent_smoke.py
  python scripts/multi_agent_smoke.py --keep-temp
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch


@dataclass(frozen=True)
class SmokeResult:
    ok: bool
    report: dict[str, Any]


def _build_config(base_home: Path) -> tuple[dict[str, Any], Path, Path]:
    from openheron.core.config import default_config

    cfg = default_config()
    cfg["agents"]["list"] = [
        {"id": "main", "default": True},
        {"id": "biz", "default": False},
    ]
    cfg["bindings"] = [
        {"agentId": "main", "match": {"channel": "local", "accountId": "personal"}},
        {"agentId": "biz", "match": {"channel": "local", "accountId": "business"}},
    ]

    agents_root = base_home / ".openheron" / "agents"
    main_dir = agents_root / "main"
    biz_dir = agents_root / "biz"
    for agent_dir in (main_dir, biz_dir):
        (agent_dir / "workspace").mkdir(parents=True, exist_ok=True)
        (agent_dir / "bootstrap").mkdir(parents=True, exist_ok=True)

    (main_dir / "bootstrap" / "AGENTS.md").write_text("MAIN_BOOTSTRAP", encoding="utf-8")
    (biz_dir / "bootstrap" / "AGENTS.md").write_text("BIZ_BOOTSTRAP", encoding="utf-8")
    return cfg, main_dir, biz_dir


def _verify(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


async def _run_smoke(temp_home: Path) -> SmokeResult:
    from openheron.app.gateway import Gateway
    from openheron.bus.events import InboundMessage
    from openheron.bus.queue import MessageBus
    from openheron.core.config import get_config_path, load_config, save_config
    from openheron.runtime.agent_runtime import agent_runtime_context
    from openheron.runtime.heartbeat_status_store import heartbeat_status_path
    from openheron.runtime.route_stats_store import route_stats_path
    from openheron.runtime.workspace_bootstrap import load_workspace_bootstrap_sections

    cfg, main_dir, biz_dir = _build_config(temp_home)
    save_config(cfg, config_path=get_config_path())
    main_cfg = {
        "id": "main",
        "workspace": str(main_dir / "workspace"),
        "agentDir": str(main_dir),
        "heartbeat": {
            "every": "30m",
            "target": "channel",
            "targetChannel": "local",
            "targetChatId": "hb-main",
            "showOk": True,
        },
    }
    biz_cfg = {
        "id": "biz",
        "workspace": str(biz_dir / "workspace"),
        "agentDir": str(biz_dir),
        "heartbeat": {
            "every": "10m",
            "target": "channel",
            "targetChannel": "local",
            "targetChatId": "hb-biz",
            "showOk": True,
        },
    }
    (main_dir / "config.json").write_text(json.dumps(main_cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (biz_dir / "config.json").write_text(json.dumps(biz_cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    loaded_cfg = load_config()

    class FakeRunner:
        async def run_async(self, **kwargs: Any):
            session_id = str(kwargs.get("session_id", ""))
            text = "HEARTBEAT_OK" if session_id.startswith("heartbeat:") else "ok"
            yield SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(text=text)]))

    with patch("openheron.app.gateway.create_runner", return_value=(FakeRunner(), object())):
        gateway = Gateway(
            agent=SimpleNamespace(name="openheron"),
            app_name="openheron",
            bus=MessageBus(),
            config=loaded_cfg,
        )

    msg_main = InboundMessage(
        channel="local",
        sender_id="u1",
        chat_id="c1",
        content="hello-main",
        metadata={"accountId": "personal", "peer": {"kind": "direct", "id": "p1"}},
    )
    msg_biz = InboundMessage(
        channel="local",
        sender_id="u2",
        chat_id="c2",
        content="hello-biz",
        metadata={"accountId": "business", "peer": {"kind": "direct", "id": "p2"}},
    )
    out_main = await gateway.process_message(msg_main)
    out_biz = await gateway.process_message(msg_biz)

    route_main = out_main.metadata.get("openheron_route", {}) if isinstance(out_main.metadata, dict) else {}
    route_biz = out_biz.metadata.get("openheron_route", {}) if isinstance(out_biz.metadata, dict) else {}

    runtime_main = gateway._router.runtime_for_agent("main")
    runtime_biz = gateway._router.runtime_for_agent("biz")
    await gateway._run_heartbeat(SimpleNamespace(reason="manual", prompt="hb-main"), agent_runtime=runtime_main)
    await gateway._run_heartbeat(SimpleNamespace(reason="manual", prompt="hb-biz"), agent_runtime=runtime_biz)

    with agent_runtime_context(runtime_main):
        bootstrap_main = load_workspace_bootstrap_sections()
    with agent_runtime_context(runtime_biz):
        bootstrap_biz = load_workspace_bootstrap_sections()

    hb_main_path = heartbeat_status_path(runtime_main.agent_dir)
    hb_biz_path = heartbeat_status_path(runtime_biz.agent_dir)
    rs_main_path = route_stats_path(runtime_main.agent_dir)
    rs_biz_path = route_stats_path(runtime_biz.agent_dir)

    hb_main = json.loads(hb_main_path.read_text(encoding="utf-8")) if hb_main_path.exists() else {}
    hb_biz = json.loads(hb_biz_path.read_text(encoding="utf-8")) if hb_biz_path.exists() else {}
    rs_main = json.loads(rs_main_path.read_text(encoding="utf-8")) if rs_main_path.exists() else {}
    rs_biz = json.loads(rs_biz_path.read_text(encoding="utf-8")) if rs_biz_path.exists() else {}

    failures: list[str] = []
    _verify(route_main.get("agentId") == "main", "route main did not map to main agent", failures)
    _verify(route_biz.get("agentId") == "biz", "route biz did not map to biz agent", failures)
    _verify(
        str(route_main.get("sessionId", "")).startswith("agent:main:"),
        "main session id is not agent-scoped",
        failures,
    )
    _verify(
        str(route_biz.get("sessionId", "")).startswith("agent:biz:"),
        "biz session id is not agent-scoped",
        failures,
    )
    _verify(hb_main_path.exists(), "main heartbeat snapshot missing", failures)
    _verify(hb_biz_path.exists(), "biz heartbeat snapshot missing", failures)
    _verify(rs_main_path.exists(), "main route stats snapshot missing", failures)
    _verify(rs_biz_path.exists(), "biz route stats snapshot missing", failures)
    _verify(rs_main.get("byAgent", {}).get("main") == 1, "main route stats count incorrect", failures)
    _verify(rs_biz.get("byAgent", {}).get("biz") == 1, "biz route stats count incorrect", failures)
    _verify(hb_main.get("last_delivery", {}).get("target_chat_id") == "hb-main", "main heartbeat target mismatch", failures)
    _verify(hb_biz.get("last_delivery", {}).get("target_chat_id") == "hb-biz", "biz heartbeat target mismatch", failures)
    _verify(
        bool(bootstrap_main) and bootstrap_main[0].content.strip() == "MAIN_BOOTSTRAP",
        "main bootstrap content mismatch",
        failures,
    )
    _verify(
        bool(bootstrap_biz) and bootstrap_biz[0].content.strip() == "BIZ_BOOTSTRAP",
        "biz bootstrap content mismatch",
        failures,
    )

    report = {
        "ok": not failures,
        "home": str(temp_home),
        "failures": failures,
        "route": {"main": route_main, "biz": route_biz},
        "paths": {
            "heartbeat_main": str(hb_main_path),
            "heartbeat_biz": str(hb_biz_path),
            "route_stats_main": str(rs_main_path),
            "route_stats_biz": str(rs_biz_path),
        },
    }
    return SmokeResult(ok=not failures, report=report)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic multi-agent local smoke checks.")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary HOME directory for inspection.")
    args = parser.parse_args()

    original_home = os.environ.get("HOME", "")
    temp_home = Path(tempfile.mkdtemp(prefix="openheron-multi-agent-smoke-")).resolve()
    os.environ["HOME"] = str(temp_home)
    try:
        result = asyncio.run(_run_smoke(temp_home))
    finally:
        if original_home:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    print(json.dumps(result.report, ensure_ascii=False))
    if args.keep_temp:
        print(f"[info] kept temp home: {temp_home}")
    else:
        shutil.rmtree(temp_home, ignore_errors=True)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
