#!/usr/bin/env python3
"""Rotate per-agent runtime artifacts by size threshold.

Current targets:
- ~/.openheron/agents/<agentId>/runtime/heartbeat_status.json
- ~/.openheron/agents/<agentId>/runtime/route_stats.json

When file size exceeds threshold, script writes a timestamped .bak copy and truncates
the original to an empty JSON object.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _rotate_json(path: Path, max_kb: int, dry_run: bool) -> bool:
    if not path.exists():
        return False
    size_kb = path.stat().st_size / 1024
    if size_kb <= max_kb:
        return False
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_suffix(path.suffix + f".{suffix}.bak")
    if dry_run:
        print(f"[dry-run] rotate {path} -> {backup} (size_kb={size_kb:.1f})")
        return True
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(json.dumps({}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[rotated] {path} -> {backup} (size_kb={size_kb:.1f})")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Rotate per-agent runtime artifact files by size.")
    parser.add_argument("--max-kb", type=int, default=512, help="Max file size in KB before rotation (default: 512).")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without writing changes.")
    args = parser.parse_args()

    base = Path.home() / ".openheron" / "agents"
    if not base.exists():
        print(f"agents directory not found: {base}")
        return 0

    rotated = 0
    for agent_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        runtime = agent_dir / "runtime"
        rotated += int(_rotate_json(runtime / "heartbeat_status.json", args.max_kb, args.dry_run))
        rotated += int(_rotate_json(runtime / "route_stats.json", args.max_kb, args.dry_run))
    print(f"rotation complete; files rotated={rotated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
