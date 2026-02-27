#!/usr/bin/env python3
"""Generate minimal multi-agent config scaffolding under ~/.openheron.

This utility creates:
- global_config.json with agents list/bindings skeleton
- per-agent config.json files under ~/.openheron/agents/<agentId>/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _agent_payload(agent_id: str) -> dict[str, object]:
    root = Path.home() / ".openheron" / "agents" / agent_id
    return {
        "id": agent_id,
        "workspace": str(root / "workspace"),
        "agentDir": str(root),
        "skills": [],
        "security": {
            "restrictToWorkspace": False,
            "allowExec": True,
            "allowNetwork": True,
            "execAllowlist": [],
        },
        "fs": {
            "workspaceOnly": False,
            "allowedPaths": [],
            "denyPaths": [],
            "readOnlyPaths": [],
        },
        "tools": {"allow": [], "deny": []},
        "heartbeat": {
            "every": "30m",
            "prompt": "",
            "ackMaxChars": 300,
            "showOk": False,
            "showAlerts": True,
            "target": "last",
            "targetChannel": "",
            "targetChatId": "",
            "activeHours": {"start": "", "end": "", "timezone": "user"},
        },
        "systemPermissions": {"browser": True, "gui": True, "screenshot": True},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold multi-agent config files.")
    parser.add_argument("--agents", default="main,biz", help="Comma-separated agent ids (default: main,biz).")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    args = parser.parse_args()

    ids = [item.strip() for item in str(args.agents).split(",") if item.strip()]
    if not ids:
        raise SystemExit("No valid agent ids provided.")

    base = Path.home() / ".openheron"
    cfg_path = base / "global_config.json"
    base.mkdir(parents=True, exist_ok=True)

    if cfg_path.exists() and not args.force:
        raise SystemExit(f"{cfg_path} already exists; rerun with --force to overwrite.")

    global_cfg = {
        "agents": {
            "defaults": {
                "workspace": str(base / "agents" / "{agentId}" / "workspace"),
                "agentDir": str(base / "agents" / "{agentId}"),
            },
            "list": [{"id": aid, "default": idx == 0} for idx, aid in enumerate(ids)],
        },
        "bindings": [],
    }
    cfg_path.write_text(json.dumps(global_cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for aid in ids:
        payload = _agent_payload(aid)
        agent_cfg = base / "agents" / aid / "config.json"
        if agent_cfg.exists() and not args.force:
            continue
        agent_cfg.parent.mkdir(parents=True, exist_ok=True)
        agent_cfg.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (agent_cfg.parent / "workspace").mkdir(parents=True, exist_ok=True)
        (agent_cfg.parent / "bootstrap").mkdir(parents=True, exist_ok=True)
        (agent_cfg.parent / "runtime").mkdir(parents=True, exist_ok=True)
    print(f"Scaffolded multi-agent config for: {', '.join(ids)}")
    print(f"Global config: {cfg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
