# openheron

`openheron` is a lightweight, skills-first agent runtime built on Google ADK.

It focuses on:

- Multi-channel gateway execution
- Local skill loading (`SKILL.md`)
- Built-in action tools (file/shell/web/message/cron/subagent)
- Persistent session + optional long-term memory

Compared with larger systems, this project keeps the core runtime compact and easy to iterate.

## Quick Start

```bash
cd openheron_root
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e .
openheron onboard
python -m openheron.cli -m "Describe what you can do"
```

`openheron onboard` initializes:

- `~/.openheron/config.json`
- `~/.openheron/workspace`

## Quick Ops Summary (from `docs/OPERATIONS.md`)

```bash
# single-turn call
python -m openheron.cli -m "Describe what you can do"
python -m openheron.cli -m "Describe what you can do" --user-id local --session-id demo001

# local gateway
python -m openheron.cli gateway-local

# multi-channel gateway
openheron gateway --channels local,feishu --interactive-local
export OPENHERON_CHANNELS=feishu
openheron gateway

# diagnostics and providers
openheron doctor
openheron skills
openheron provider list
openheron provider status
openheron provider login github-copilot
openheron provider login openai-codex
```

WhatsApp bridge quick flow:

```bash
openheron channels login
openheron channels bridge start
openheron channels bridge status
openheron channels bridge stop
scripts/whatsapp_bridge_e2e.sh smoke
```

Cron quick flow (jobs run only while gateway is running):

```bash
openheron cron list
openheron cron add --name daily --message "daily report" --cron "0 9 * * 1-5" --tz Asia/Shanghai
openheron cron status
```

## Common Commands

```bash
# local gateway
python -m openheron.cli gateway-local

# multi-channel gateway
openheron gateway --channels local,feishu --interactive-local

# diagnostics
openheron doctor
openheron skills
```

## Core Capabilities

- Runtime: Google ADK (`LlmAgent` + tools + callbacks)
- Session: SQLite-backed ADK session service
- Memory backends: `in_memory` / `markdown`
- Context compaction: ADK `EventsCompactionConfig`
- Slash commands: `/help` and `/new`
- Channel bridge: local + mainstream chat connectors

## Project Layout

```text
openheron_root/
├── README.md
├── docs/
├── openheron/
├── tests/
└── scripts/
```

## Documentation

Detailed docs are in [`docs/`](./docs/):

- [`docs/PROJECT_OVERVIEW.md`](./docs/PROJECT_OVERVIEW.md)
- [`docs/OPERATIONS.md`](./docs/OPERATIONS.md)
- [`docs/CONFIGURATION.md`](./docs/CONFIGURATION.md)
- [`docs/MCP_SECURITY.md`](./docs/MCP_SECURITY.md)
- [`docs/README.md`](./docs/README.md)

## Testing

```bash
source .venv/bin/activate
pytest -q
```
