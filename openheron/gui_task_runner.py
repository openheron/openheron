"""Multi-step GUI task runner built on top of computer_use."""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from openai import OpenAI

from .gui_executor import (
    DEFAULT_GUI_API_KEY_ENV,
    DEFAULT_GUI_BASE_URL_ENV,
    DEFAULT_GUI_MODEL_ENV,
    CapturedScreen,
    PyAutoGuiRuntime,
    execute_gui_action,
)


DEFAULT_GUI_PLANNER_MODEL_ENV = "OPENHERON_GUI_PLANNER_MODEL"
DEFAULT_GUI_PLANNER_API_KEY_ENV = "OPENHERON_GUI_PLANNER_API_KEY"
DEFAULT_GUI_PLANNER_BASE_URL_ENV = "OPENHERON_GUI_PLANNER_BASE_URL"
DEFAULT_GUI_TASK_MAX_STEPS_ENV = "OPENHERON_GUI_TASK_MAX_STEPS"
DEFAULT_GUI_TASK_PARSE_RETRIES_ENV = "OPENHERON_GUI_TASK_PARSE_RETRIES"
DEFAULT_GUI_TASK_MAX_NO_PROGRESS_STEPS_ENV = "OPENHERON_GUI_TASK_MAX_NO_PROGRESS_STEPS"
DEFAULT_GUI_TASK_MAX_REPEAT_ACTIONS_ENV = "OPENHERON_GUI_TASK_MAX_REPEAT_ACTIONS"


def _parse_action_json(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if text.startswith("```json"):
        text = text.replace("```json", "", 1).strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return json.loads(text)


def _needs_correction_hint(history: list[dict[str, Any]]) -> bool:
    """Return True when latest execute step did not change the screen."""
    if not history:
        return False
    last = history[-1]
    return (
        str(last.get("type", "")).strip().lower() == "execute"
        and last.get("screen_changed") is False
        and bool(last.get("ok", False))
    )


class GuiTaskRunner:
    """Run a multi-step GUI task by iterating planner + computer_use execution."""

    def __init__(
        self,
        *,
        planner_model: str,
        planner_api_key: str,
        planner_base_url: str | None = None,
        action_executor: Callable[..., dict[str, Any]] | None = None,
        runtime: Any | None = None,
        planner_client: Any | None = None,
        max_parse_retries: int = 1,
        max_no_progress_steps: int = 3,
        max_repeat_actions: int = 3,
    ) -> None:
        self._planner_model = planner_model
        self._planner_client = planner_client or OpenAI(
            api_key=planner_api_key,
            base_url=planner_base_url or None,
        )
        self._action_executor = action_executor or execute_gui_action
        self._runtime = runtime or PyAutoGuiRuntime()
        self._max_parse_retries = max(0, int(max_parse_retries))
        self._max_no_progress_steps = max(1, int(max_no_progress_steps))
        self._max_repeat_actions = max(1, int(max_repeat_actions))

    def _messages(
        self,
        task: str,
        current_plan: str,
        saved_info: dict[str, str],
        history: list[dict[str, Any]],
        screen: CapturedScreen,
    ) -> list[dict[str, Any]]:
        if not history:
            history_text = "No previous GUI steps."
        else:
            lines: list[str] = []
            for idx, item in enumerate(history[-8:], 1):
                lines.append(
                    f"{idx}. type={item.get('type')} action={item.get('action')} changed={item.get('screen_changed')} "
                    f"retries={item.get('retries_used')} ok={item.get('ok')}"
                )
            history_text = "\n".join(lines)
        if not saved_info:
            saved_info_text = "No saved info."
        else:
            saved_info_text = "\n".join([f"- {k}: {v}" for k, v in saved_info.items()])
        correction_hint = ""
        if _needs_correction_hint(history):
            correction_hint = (
                "Correction hint:\n"
                "- The previous execute step did not change the screen.\n"
                "- First diagnose focus/state, then issue a more concrete action.\n"
                "- Do not repeat the same vague command.\n\n"
            )

        return [
            {
                "role": "system",
                "content": (
                    "You are a GUI task planner. Decide only one next step.\n"
                    "Return strict JSON with schema:\n"
                    '{"thinking":"...","action":{"type":"execute|save_info|modify_plan|reply","params":{"action":"...","key":"...","value":"...","new_plan":"...","message":"..."}}}\n'
                    "Rules:\n"
                    "- Use execute for one concrete GUI action.\n"
                    "- Use save_info when a detail must be remembered for later steps.\n"
                    "- Use modify_plan when plan should be updated.\n"
                    "- Use reply only when task is complete.\n"
                    "- Keep actions atomic.\n"
                    "- Execute params.action must be specific and observable.\n"
                    "- Avoid vague actions like: open application, search, type text, continue, next.\n"
                    "- Good action examples: click browser icon in dock, click address bar, type 'openheron', press Enter."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Task:\n{task}\n\n"
                            f"Current plan:\n{current_plan}\n\n"
                            f"Saved info:\n{saved_info_text}\n\n"
                            f"Recent history:\n{history_text}\n\n"
                            f"{correction_hint}"
                            "Decide next action."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{screen.base64_png}"},
                    },
                ],
            },
        ]

    def _plan_next(
        self,
        task: str,
        current_plan: str,
        saved_info: dict[str, str],
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        parse_attempt = 0
        last_error = ""
        while parse_attempt <= self._max_parse_retries:
            screen = self._runtime.capture()
            messages = self._messages(task, current_plan, saved_info, history, screen)
            completion = self._planner_client.chat.completions.create(
                model=self._planner_model,
                messages=messages,
            )
            raw = str(completion.choices[0].message.content or "")
            try:
                parsed = _parse_action_json(raw)
                action = parsed.get("action")
                if not isinstance(action, dict):
                    raise ValueError("missing action object")
                return parsed
            except Exception as exc:
                last_error = str(exc)
                parse_attempt += 1
                if parse_attempt > self._max_parse_retries:
                    raise ValueError(
                        f"failed to parse task planner output after {self._max_parse_retries + 1} attempts: {last_error}"
                    ) from exc
        raise ValueError("planner parsing fallback reached unexpectedly")

    def run(self, task: str, *, max_steps: int = 8, dry_run: bool = False) -> dict[str, Any]:
        """Run task loop until reply or max steps."""
        history: list[dict[str, Any]] = []
        current_plan = task
        saved_info: dict[str, str] = {}

        def _final_summary() -> str:
            if saved_info:
                saved_info_text = ", ".join([f"{k}={v}" for k, v in saved_info.items()])
            else:
                saved_info_text = "none"
            return f"plan={current_plan}; saved_info={saved_info_text}; steps={len(history)}"

        def _result(
            *,
            ok: bool,
            finished: bool,
            status_code: str,
            message: str | None = None,
            error: str | None = None,
            last_error_type: str | None = None,
        ) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "ok": ok,
                "task": task,
                "steps": history,
                "step_count": len(history),
                "current_plan": current_plan,
                "saved_info": saved_info,
                "saved_info_snapshot": dict(saved_info),
                "final_summary": _final_summary(),
                "finished": finished,
                "status_code": status_code,
                "last_error_type": last_error_type or "none",
            }
            if message is not None:
                payload["message"] = message
            if error is not None:
                payload["error"] = error
            return payload

        for step in range(1, max_steps + 1):
            planned = self._plan_next(task, current_plan, saved_info, history)
            action = planned.get("action", {})
            action_type = str(action.get("type", "")).strip().lower()
            params = action.get("params", {}) if isinstance(action.get("params"), dict) else {}

            if action_type == "reply":
                message = str(params.get("message", "Task finished")).strip() or "Task finished"
                return _result(
                    ok=True,
                    finished=True,
                    status_code="completed",
                    message=message,
                )

            if action_type == "save_info":
                key = str(params.get("key", "")).strip()
                value = str(params.get("value", "")).strip()
                if not key:
                    return _result(
                        ok=False,
                        finished=False,
                        status_code="failed",
                        error="planner save_info action missing params.key",
                        last_error_type="missing_save_info_key",
                    )
                saved_info[key] = value
                history.append(
                    {
                        "step": step,
                        "type": "save_info",
                        "thinking": planned.get("thinking", ""),
                        "action": f"save_info:{key}",
                        "ok": True,
                        "screen_changed": None,
                        "retries_used": 0,
                        "error": None,
                    }
                )
                continue

            if action_type == "modify_plan":
                new_plan = str(params.get("new_plan", "")).strip()
                if not new_plan:
                    return _result(
                        ok=False,
                        finished=False,
                        status_code="failed",
                        error="planner modify_plan action missing params.new_plan",
                        last_error_type="missing_modify_plan_value",
                    )
                current_plan = new_plan
                history.append(
                    {
                        "step": step,
                        "type": "modify_plan",
                        "thinking": planned.get("thinking", ""),
                        "action": "modify_plan",
                        "ok": True,
                        "screen_changed": None,
                        "retries_used": 0,
                        "error": None,
                    }
                )
                continue

            if action_type != "execute":
                return _result(
                    ok=False,
                    finished=False,
                    status_code="failed",
                    error=f"unsupported planner action type: {action_type}",
                    last_error_type="unsupported_action_type",
                )

            action_text = str(params.get("action", "")).strip()
            if not action_text:
                return _result(
                    ok=False,
                    finished=False,
                    status_code="failed",
                    error="planner execute action missing params.action",
                    last_error_type="missing_execute_action",
                )

            result = self._action_executor(action=action_text, dry_run=dry_run)
            step_record = {
                "step": step,
                "type": "execute",
                "thinking": planned.get("thinking", ""),
                "action": action_text,
                "ok": bool(result.get("ok", False)),
                "screen_changed": result.get("screen_changed"),
                "retries_used": result.get("retries_used"),
                "error": result.get("error"),
            }
            history.append(step_record)
            if not step_record["ok"]:
                return _result(
                    ok=False,
                    finished=False,
                    status_code="failed",
                    error=f"computer_use failed at step {step}: {step_record.get('error')}",
                    last_error_type="executor_error",
                )

            # Stall guard: stop early if progress is repeatedly absent.
            no_progress_count = 0
            for item in reversed(history):
                if item.get("type") != "execute":
                    break
                if item.get("screen_changed") is False:
                    no_progress_count += 1
                else:
                    break
            if no_progress_count >= self._max_no_progress_steps:
                return _result(
                    ok=False,
                    finished=False,
                    status_code="no_progress",
                    error=(
                        f"no progress for {no_progress_count} consecutive execute steps "
                        f"(threshold={self._max_no_progress_steps})"
                    ),
                    last_error_type="no_progress_stall",
                )

            repeated_action_count = 0
            for item in reversed(history):
                if item.get("type") != "execute":
                    break
                if str(item.get("action", "")).strip() == action_text:
                    repeated_action_count += 1
                else:
                    break
            if repeated_action_count >= self._max_repeat_actions:
                return _result(
                    ok=False,
                    finished=False,
                    status_code="no_progress",
                    error=(
                        f"same action repeated {repeated_action_count} times "
                        f"(threshold={self._max_repeat_actions}): {action_text}"
                    ),
                    last_error_type="repeated_action_stall",
                )

        return _result(
            ok=False,
            finished=False,
            status_code="max_steps",
            error=f"max steps reached ({max_steps})",
            last_error_type="max_steps_reached",
        )


def execute_gui_task(
    *,
    task: str,
    max_steps: int | None = None,
    dry_run: bool = False,
    planner_model: str | None = None,
    planner_api_key: str | None = None,
    planner_base_url: str | None = None,
) -> dict[str, Any]:
    """Run a multi-step GUI task using environment-resolved planner settings."""
    resolved_planner_model = (
        planner_model
        or os.getenv(DEFAULT_GUI_PLANNER_MODEL_ENV, "")
        or os.getenv(DEFAULT_GUI_MODEL_ENV, "")
    ).strip()
    resolved_planner_api_key = (
        planner_api_key
        or os.getenv(DEFAULT_GUI_PLANNER_API_KEY_ENV, "")
        or os.getenv(DEFAULT_GUI_API_KEY_ENV, "")
        or os.getenv("OPENAI_API_KEY", "")
    ).strip()
    resolved_planner_base_url = (
        planner_base_url
        or os.getenv(DEFAULT_GUI_PLANNER_BASE_URL_ENV, "")
        or os.getenv(DEFAULT_GUI_BASE_URL_ENV, "")
    ).strip() or None
    resolved_max_steps = max_steps
    if resolved_max_steps is None:
        raw_steps = os.getenv(DEFAULT_GUI_TASK_MAX_STEPS_ENV, "").strip()
        try:
            resolved_max_steps = int(raw_steps) if raw_steps else 8
        except ValueError:
            resolved_max_steps = 8
    resolved_max_steps = max(1, int(resolved_max_steps))
    raw_parse_retries = os.getenv(DEFAULT_GUI_TASK_PARSE_RETRIES_ENV, "").strip()
    try:
        max_parse_retries = max(0, int(raw_parse_retries)) if raw_parse_retries else 1
    except ValueError:
        max_parse_retries = 1
    raw_no_progress_steps = os.getenv(DEFAULT_GUI_TASK_MAX_NO_PROGRESS_STEPS_ENV, "").strip()
    try:
        max_no_progress_steps = max(1, int(raw_no_progress_steps)) if raw_no_progress_steps else 3
    except ValueError:
        max_no_progress_steps = 3
    raw_repeat_actions = os.getenv(DEFAULT_GUI_TASK_MAX_REPEAT_ACTIONS_ENV, "").strip()
    try:
        max_repeat_actions = max(1, int(raw_repeat_actions)) if raw_repeat_actions else 3
    except ValueError:
        max_repeat_actions = 3

    if not resolved_planner_model:
        raise ValueError(
            f"Missing GUI planner model. Set {DEFAULT_GUI_PLANNER_MODEL_ENV} or {DEFAULT_GUI_MODEL_ENV}."
        )
    if not resolved_planner_api_key:
        raise ValueError(
            f"Missing GUI planner api key. Set {DEFAULT_GUI_PLANNER_API_KEY_ENV}, {DEFAULT_GUI_API_KEY_ENV}, or OPENAI_API_KEY."
        )

    runner = GuiTaskRunner(
        planner_model=resolved_planner_model,
        planner_api_key=resolved_planner_api_key,
        planner_base_url=resolved_planner_base_url,
        max_parse_retries=max_parse_retries,
        max_no_progress_steps=max_no_progress_steps,
        max_repeat_actions=max_repeat_actions,
    )
    return runner.run(task, max_steps=resolved_max_steps, dry_run=dry_run)


__all__ = ["GuiTaskRunner", "execute_gui_task"]
