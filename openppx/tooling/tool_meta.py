"""Static metadata for built-in openppx tools."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolMeta:
    """Runtime-neutral metadata for scheduling and policy decisions."""

    read_only: bool
    exclusive: bool = False
    concurrency_safe: bool = True
    category: str = "general"
    risk: str = "low"


TOOL_META: dict[str, ToolMeta] = {
    "load_artifacts": ToolMeta(read_only=True, category="memory"),
    "list_skills": ToolMeta(read_only=True, category="skill"),
    "read_skill": ToolMeta(read_only=True, category="skill"),
    "read_file": ToolMeta(read_only=True, category="filesystem"),
    "list_dir": ToolMeta(read_only=True, category="filesystem"),
    "glob": ToolMeta(read_only=True, category="filesystem"),
    "grep": ToolMeta(read_only=True, category="filesystem"),
    "web_search": ToolMeta(read_only=True, category="web"),
    "web_fetch": ToolMeta(read_only=True, category="web"),
    "write_file": ToolMeta(read_only=False, category="filesystem", risk="medium"),
    "edit_file": ToolMeta(read_only=False, category="filesystem", risk="medium"),
    "message": ToolMeta(read_only=False, category="communication", risk="high"),
    "message_image": ToolMeta(read_only=False, category="communication", risk="high"),
    "message_file": ToolMeta(read_only=False, category="communication", risk="high"),
    "cron": ToolMeta(read_only=False, category="automation", risk="high"),
    "spawn_subagent": ToolMeta(read_only=False, category="delegation", risk="high"),
    "exec": ToolMeta(read_only=False, exclusive=True, concurrency_safe=False, category="process", risk="high"),
    "process": ToolMeta(read_only=False, exclusive=True, concurrency_safe=False, category="process", risk="high"),
    "browser": ToolMeta(read_only=False, exclusive=True, concurrency_safe=False, category="browser", risk="high"),
    "computer_task": ToolMeta(read_only=False, exclusive=True, concurrency_safe=False, category="gui", risk="high"),
    "computer_use": ToolMeta(read_only=False, exclusive=True, concurrency_safe=False, category="gui", risk="high"),
}


def get_tool_meta(name: str) -> ToolMeta | None:
    """Return metadata for a built-in tool by public tool name."""

    return TOOL_META.get(name)
