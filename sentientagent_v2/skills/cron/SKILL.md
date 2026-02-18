---
name: cron
description: Schedule reminders and recurring tasks.
---

# Cron

Use the `cron` tool to schedule reminders or recurring tasks.

## Core Rule

`message` MUST describe what the system should do at trigger time.
Treat it as executable task instruction for the agent, not as a title or raw note.

## Message Field (Most Important)

When building `cron(action="add", ...)`:

1. `message` should include the action and expected output behavior.
2. For reminder-like jobs, explicitly say whether output must be exact text.
3. Avoid ambiguous `message` values like only a number or a noun phrase.

Bad examples (ambiguous):
```
cron(action="add", message="139121235123", at="<ISO>")
cron(action="add", message="meeting", every_seconds=1200)
```

Good examples (explicit action):
```
cron(action="add", message="你是提醒助手。请只输出：时间到了。不要添加其他内容。", at="<ISO>")
cron(action="add", message="你是提醒助手。请只输出：139121235123。不要解释，不要改写。", at="<ISO>")
cron(action="add", message="请检查项目状态并输出三条摘要，每条不超过20字。", every_seconds=600)
```

## Scheduling Modes

1. Interval: `every_seconds`
2. Cron expression: `cron_expr` (+ optional `tz`)
3. One-time: `at` (absolute ISO datetime; usually auto-delete after execution)

## Time Expression Mapping

| User says | Parameters |
|-----------|------------|
| every 20 minutes | every_seconds: 1200 |
| every hour | every_seconds: 3600 |
| every day at 8am | cron_expr: "0 8 * * *" |
| weekdays at 5pm | cron_expr: "0 17 * * 1-5" |
| at a specific time | at: ISO datetime string |

## Relative Time Rule (Required)

For requests like "in 20 minutes", "after 2 hours", or "过2分钟/1小时后执行",
the reference point MUST be the current conversation message time (request receive time),
NOT gateway startup time.

Workflow:

1. Read request receive time as `now`.
2. Compute `at = now + delta`.
3. Call `cron(action="add", message="...", at="<ISO from step 2>")`.

Example:

- User says: "2分钟之后，发一个“139121235123”的消息给我"
- Correct cron call shape:
```
cron(
  action="add",
  message="你是提醒助手。请只输出：139121235123。不要解释，不要改写。",
  at="<ISO datetime computed from current request time>"
)
```

## Basic Management

```
cron(action="list")
cron(action="remove", job_id="abc123")
```
