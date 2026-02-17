# sentientagent_v2

`sentientagent_v2` is a lightweight, skills-first agent built with Google ADK, focused on learning and education use cases.

Compared to nanobot, sentientagent_v2 is intentionally smaller and simpler.
You can think of sentientagent_v2 as a "Hello World" edition of the OpenClaw-style agent workflow.

## Scope

- Keeps: local skill discovery and loading (`SKILL.md`)
- Adds: minimal bus/channel gateway with pluggable channels (`local`, `feishu`)
- Runtime: Google ADK (`LlmAgent` + function tools)
- Bundles built-in skills under `sentientagent_v2/skills`
- Provides core tools for file, shell, web, messaging, and scheduling workflows

## Project Structure

```text
sentientagent_v2/
├── pyproject.toml
├── README.md
└── sentientagent_v2/
    ├── __init__.py
    ├── agent.py
    ├── cli.py
    ├── skills.py
    └── skills/
        └── general/
            └── SKILL.md
```

## Skill Model

`sentientagent_v2` discovers skills from:

1. `SENTIENTAGENT_V2_WORKSPACE/skills/*/SKILL.md` (workspace, higher priority)
2. Built-in `sentientagent_v2/skills/*/SKILL.md`

The agent exposes two skill tools:

- `list_skills()`: list available skills as JSON
- `read_skill(name)`: read full `SKILL.md` content

## Built-in Action Tools

- `read_file`, `write_file`, `edit_file`, `list_dir`
- `exec` (implemented by `exec_command`)
- `web_search`, `web_fetch`
- `message` (local outbox log)
- `cron` (local persisted add/list/remove)

## Installation

```bash
cd sentientagent_v2
pip install -e .
```

## Onboard (Recommended)

Initialize local config and workspace:

```bash
sentientagent_v2 onboard
```

This creates:

- `~/.sentientagent_v2/config.json`
- `~/.sentientagent_v2/workspace`

Gateway/doctor/message commands will auto-load this config file and map it to runtime env vars.
日常使用建议只改这个 `config.json`，不要频繁手工 `export`。

## Run

### Single-turn request (recommended)

```bash
cd sentientagent_v2
python -m sentientagent_v2.cli -m "Describe what you can do"
```

You can also pass explicit identifiers:

```bash
python -m sentientagent_v2.cli -m "Describe what you can do" --user-id local --session-id demo001
```

### ADK CLI mode

```bash
adk run sentientagent_v2
```

### Wrapper CLI

```bash
sentientagent_v2 run
```

### Utilities

```bash
sentientagent_v2 skills
sentientagent_v2 doctor
```

### Gateway: local channel

```bash
python -m sentientagent_v2.cli gateway-local
```

### Gateway: channel mode (including Feishu)

```bash
sentientagent_v2 gateway --channels local,feishu --interactive-local
```

Or use env default:

```bash
export SENTIENTAGENT_V2_CHANNELS=feishu
sentientagent_v2 gateway
```

Recommended for Feishu: set channels and Feishu credentials in `~/.sentientagent_v2/config.json`,
then run:

```bash
sentientagent_v2 gateway
```

## Classic Usage Examples

```bash
python -m sentientagent_v2.cli -m "search for the latest research progress today, and create a PPT for me."
python -m sentientagent_v2.cli -m "download all PDF files from this page: https://bbs.kangaroo.study/forum.php?mod=viewthread&tid=467"
```

## Testing

```bash
source .venv/bin/activate
python -m pytest -q
```

## Environment Variables

`sentientagent_v2` supports both:

- config file: `~/.sentientagent_v2/config.json` (recommended)
- shell env vars (higher priority, overrides config values)

通常不需要设置任何环境变量，直接在 `config.json` 里填：

- `keys.googleApiKey`（必填，LLM 调用）
- `channels.enabled` 和 `channels.feishu.*`（启用 Feishu 时）

只在“临时覆盖”时才建议使用 env，例如：

- `GOOGLE_API_KEY`
- `SENTIENTAGENT_V2_CHANNELS`
- `SENTIENTAGENT_V2_DEBUG`

## Feishu Dependency

Install Feishu SDK only when needed:

```bash
pip install -e '.[feishu]'
```

If your environment uses a SOCKS proxy and you see
`python-socks is required to use a SOCKS proxy`, install:

```bash
pip install python-socks
```

## Config Example

```json
{
  "agent": {
    "model": "gemini-3-flash-preview",
    "workspace": "~/.sentientagent_v2/workspace",
    "builtinSkillsDir": ""
  },
  "session": {
    "backend": "memory",
    "dbUrl": ""
  },
  "channels": {
    "enabled": ["feishu"],
    "feishu": {
      "appId": "cli_xxx",
      "appSecret": "xxx",
      "encryptKey": "",
      "verificationToken": ""
    }
  },
  "keys": {
    "googleApiKey": "your_google_api_key",
    "braveApiKey": ""
  },
  "debug": false
}
```

## Acknowledgements

This project is inspired by and partially adapted from [nanobot](https://github.com/HKUDS/nanobot).
Some implementation patterns and skill-related resources are derived from that project.
