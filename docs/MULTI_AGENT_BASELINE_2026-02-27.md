# 多智能体发布基线（2026-02-27）

## 本地验证基线

1. `python scripts/multi_agent_smoke.py`：通过
2. `pytest -q tests/test_cli.py tests/test_bus_gateway.py`：通过
3. `pytest -q tests/test_runtime_heartbeat_status_store.py tests/test_runtime_workspace_bootstrap.py tests/test_config.py`：通过

## 能力基线

1. per-agent 目录隔离：workspace/sessions/memory/auth/runtime
2. per-agent heartbeat：配置、执行、快照、CLI 查询
3. per-agent route stats：快照、CLI 查询、doctor 汇总
4. per-agent bootstrap：`agents/<id>/bootstrap/*.md` 优先加载
5. doctor `observability.byAgent`：已上线

## 风险与后续

1. 需执行真实渠道长稳测试（见 `MULTI_AGENT_LONGRUN_PLAN.md`）。
2. 兼容层已在 Phase 1（只写新路径 + 读回退旧路径），待进入 Phase 2。
