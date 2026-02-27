# 多智能体真实渠道长稳测试计划

目标：在真实渠道流量下验证 24h-72h 稳定性。

## 覆盖范围

1. 路由准确率：`channel + accountId + peer` 命中是否符合预期。
2. 会话隔离：不同 agent/session 不串线。
3. 心跳可达性：每 agent heartbeat 状态与投递目标正确。
4. 观测完整性：per-agent `route_stats` / `heartbeat_status` 快照持续更新。

## 执行步骤

1. 选择至少 2 个渠道（例如 `local + whatsapp` 或 `local + telegram`）。
2. 为每个渠道准备至少 2 个 agent 路由目标（例如 `main/biz`）。
3. 连续运行网关 24h（建议扩展到 72h）：
   - 每小时执行：
     - `openheron doctor --json`
     - `openheron routes stats --json --agent-id <id> --window-hours 1`
     - `openheron heartbeat status --json --agent-id <id>`
4. 在窗口内注入定时测试消息，覆盖 account/peer 两级路由。

## 通过标准

1. 无会话串线或错误路由事件。
2. `doctor --json` 无阻断 `issues`。
3. 目标 agent 的快照文件持续更新且无长时间缺失。
4. 高优先级异常（进程崩溃、路由冲突、权限误放大）为 0。

## 建议产物

1. 每小时 JSON 快照归档（按 `date/agentId` 目录）。
2. 最终汇总报告：
   - 运行时长
   - 消息总量
   - 路由准确率
   - 异常清单与修复动作
