"""Minimal CLI helpers for sentientagent_v2."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .skills import get_registry


def _cmd_skills() -> int:
    registry = get_registry()
    payload = [
        {
            "name": info.name,
            "description": info.description,
            "source": info.source,
            "location": str(info.path),
        }
        for info in registry.list_skills()
    ]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_doctor() -> int:
    issues: list[str] = []
    if shutil.which("adk") is None:
        issues.append("Missing `adk` CLI. Install with: pip install google-adk")

    registry = get_registry()
    skills_count = len(registry.list_skills())
    print(f"Workspace: {registry.workspace}")
    print(f"Detected skills: {skills_count}")

    if issues:
        print("\nIssues:")
        for item in issues:
            print(f"- {item}")
        return 1

    print("Environment looks good.")
    return 0


def _cmd_run(passthrough_args: list[str]) -> int:
    if shutil.which("adk") is None:
        print("`adk` CLI not found. Install with: pip install google-adk")
        return 1

    agent_dir = Path(__file__).parent.resolve()
    cmd = ["adk", "run", str(agent_dir), *passthrough_args]
    return subprocess.call(cmd)


def _extract_text(content: types.Content | None) -> str:
    if content is None or not content.parts:
        return ""
    chunks: list[str] = []
    for part in content.parts:
        text = getattr(part, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def _cmd_message(message: str, user_id: str, session_id: str) -> int:
    from .agent import root_agent

    _debug(
        "llm.request",
        {
            "user_id": user_id,
            "session_id": session_id,
            "message": message,
            "model": getattr(root_agent, "model", None),
            "tools": [getattr(t, "__name__", str(t)) for t in getattr(root_agent, "tools", [])],
        },
    )

    async def _run_once() -> str:
        session_service = InMemorySessionService()
        app_name = root_agent.name
        await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
        runner = Runner(agent=root_agent, app_name=app_name, session_service=session_service)
        request = types.UserContent(parts=[types.Part.from_text(text=message)])

        final = ""
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=request):
            _debug_event(event)
            text = _extract_text(event.content)
            if text:
                final = text
        return final

    try:
        final_text = asyncio.run(_run_once())
    except Exception as exc:
        print(f"Error running agent: {exc}")
        return 1

    if not final_text:
        print("(no response)")
        return 0
    print(final_text)
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="sentientagent_v2",
        description="Lightweight skills-only agent based on Google ADK.",
    )
    parser.add_argument("-m", "--message", help="Run a single-turn request and print the response.")
    parser.add_argument("--user-id", default="local-user", help="User id for ADK session mode.")
    parser.add_argument(
        "--session-id",
        default="",
        help="Session id for ADK session mode (auto-generated if omitted).",
    )

    subparsers = parser.add_subparsers(dest="command", required=False)
    subparsers.add_parser("skills", help="List discovered skills as JSON.")
    subparsers.add_parser("doctor", help="Check local runtime prerequisites.")

    run_parser = subparsers.add_parser("run", help="Run `adk run` for this agent.")
    run_parser.add_argument("adk_args", nargs=argparse.REMAINDER, help="Extra args passed to adk run.")

    args = parser.parse_args(argv)
    if args.message:
        sid = args.session_id or uuid.uuid4().hex[:12]
        code = _cmd_message(args.message, user_id=args.user_id, session_id=sid)
    elif args.command == "skills":
        code = _cmd_skills()
    elif args.command == "doctor":
        code = _cmd_doctor()
    elif args.command == "run":
        code = _cmd_run(args.adk_args)
    else:
        parser.print_help()
        code = 2

    raise SystemExit(code)


def _debug_enabled() -> bool:
    return os.getenv("SENTIENTAGENT_V2_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _debug(tag: str, payload: object) -> None:
    if not _debug_enabled():
        return
    try:
        body = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        body = str(payload)
    print(f"[DEBUG] {tag}: {body}", file=sys.stderr)


def _debug_event(event: object) -> None:
    if not _debug_enabled():
        return
    content = getattr(event, "content", None)
    author = getattr(event, "author", "")
    turn_complete = getattr(event, "turn_complete", None)
    finish_reason = getattr(event, "finish_reason", None)
    error_code = getattr(event, "error_code", None)
    error_message = getattr(event, "error_message", None)
    actions = getattr(event, "actions", None)
    parts_log: list[dict[str, object]] = []
    if content and getattr(content, "parts", None):
        for part in content.parts:
            row: dict[str, object] = {}
            text = getattr(part, "text", None)
            if text:
                row["text"] = text
            function_call = getattr(part, "function_call", None)
            if function_call:
                row["function_call"] = {
                    "name": getattr(function_call, "name", ""),
                    "args": getattr(function_call, "args", {}),
                }
            function_response = getattr(part, "function_response", None)
            if function_response:
                row["function_response"] = {
                    "name": getattr(function_response, "name", ""),
                    "response": getattr(function_response, "response", {}),
                }
            if row:
                parts_log.append(row)
    _debug(
        "llm.event",
        {
            "author": author,
            "turn_complete": turn_complete,
            "finish_reason": finish_reason,
            "error_code": error_code,
            "error_message": error_message,
            "actions": str(actions) if actions is not None else None,
            "parts": parts_log,
        },
    )


if __name__ == "__main__":
    main()
