---
name: self-observe
description: Observe openheron runtime health with token usage, gateway/heartbeat status, error logs, and quick diagnostics.
---

# Self Observe Skill

Use this skill when the user asks for agent self-inspection, runtime health checks, or diagnostics such as token cost, error logs, and service status.

## What To Check

1. Token usage:
```bash
openheron token stats --json
openheron token stats --provider google --limit 50 --json
openheron token stats --provider openai --limit 50 --json
```

2. Runtime status:
```bash
openheron gateway status --json
openheron heartbeat status --json
openheron cron status
openheron provider status --json
```

3. Error logs (read-only):
```bash
tail -n 200 ~/.openheron/log/gateway.err.log
rg -n "ERROR|Error|Traceback|Exception|failed|timeout" ~/.openheron/log/gateway.err.log ~/.openheron/log/gateway.out.log ~/.openheron/log/gateway.debug.log
```

4. SQLite quick verification (if `sqlite3` exists):
```bash
sqlite3 ~/.openheron/token_usage.db "SELECT provider, COUNT(*) AS requests, SUM(total_tokens) AS total_tokens FROM llm_token_usage_events GROUP BY provider ORDER BY total_tokens DESC;"
sqlite3 ~/.openheron/token_usage.db "SELECT response_at, provider, model, request_tokens, response_tokens, total_tokens FROM llm_token_usage_events ORDER BY response_at_ms DESC LIMIT 20;"
```

## Fast Path

Generate one consolidated report:

```bash
bash openheron/skills/self-observe/scripts/self_status_report.sh
```

## Output Format

When reporting to user, include:

1. Runtime Summary: gateway/heartbeat/provider/cron highlights.
2. Token Summary: total requests/tokens and provider split.
3. Recent Errors: latest error signatures with file and timestamp.
4. Risks: what might break soon (missing usage data, repeated failures, disconnected provider).
5. Next Actions: concrete commands to validate/fix.

## Guardrails

- Keep checks read-only by default.
- Do not delete or truncate logs unless the user explicitly asks.
- If status/log files are missing, report "not found" explicitly instead of guessing.
- Prefer structured output (`--json`) first, then summarize in natural language.
