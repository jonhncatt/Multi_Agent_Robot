# Smoke Matrix

English version: [smoke_matrix.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/smoke_matrix.md)

| 层级 | 入口 | 目的 | 是否进 CI | 何时运行 |
| --- | --- | --- | --- | --- |
| baseline smoke | `python scripts/demo_minimal_agent_os.py --check` | 验证 kernel/runtime 最小路径仍然能启动并返回健康结果 | 是 | 每次 push / PR |
| module smoke | `python scripts/demo_research_module.py --check` | 验证第二正式模块仍能通过 `KernelHost` dispatch 并返回 research 结果 | 是 | 每次 push / PR |
| swarm smoke | `python scripts/demo_research_swarm.py --check` | 验证模块内 Swarm 的 fan-out、join、degradation 仍能端到端运行 | 是 | 每次 push / PR |
| release smoke | `/api/kernel/shadow/smoke`、`/api/kernel/shadow/contracts`、`/api/kernel/shadow/replay` | 在发布前或迁移前验证候选版本 | 否 | 发布准备 / 迁移验证 |

## 分层规则

- baseline smoke 保护平台启动和最小可用 dispatch 路径。
- module smoke 保护非 office 模块健康；在新模块正式化之前，当前默认聚焦 `research_module`。
- swarm smoke 保护当前业务向的 Swarm MVP，而不是未来的 scheduler 重写。
- release smoke 比较重，只适合发布或迁移流程，不适合默认 CI 分支门禁。
