# 平台运营总览

这是当前平台状态的单一运营入口。它不会创建第二套状态系统。下面所有状态都来自现有 artifacts、eval summaries、metrics、smoke 文档、replay samples 和 runbook 的汇总。

English version: [platform_operations_overview.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/platform_operations_overview.md)

## 当前阶段

当前阶段：`平台运营与汇报整理`

当前平台状态：

- 平台基线：稳定
- office 基线：gate 绿色，baseline smoke 绿色
- `research_module`：已进入可运营、可回归状态
- Swarm MVP：已进入可运营、可展示、可解释状态
- replay / smoke / eval：已经足以支撑发布前检查和状态汇报，但 replay 样本库规模仍然刻意保持轻量

## 三条主线当前状态

| 主线 | 当前状态 | 最新依据 | 运营入口 |
| --- | --- | --- | --- |
| office baseline | 稳定 | `artifacts/evals/regression-summary.json` 中 office gate `20/20` 通过 | `docs/operations/quality_gates.zh-CN.md` |
| research_module | 运营中 | `artifacts/evals/research-gate-summary.json` 中 research gate `6/6` 通过，且已有指标与运营文档 | `docs/operations/research_module_operations.zh-CN.md` |
| Swarm MVP | 运营中 | `artifacts/evals/swarm-gate-summary.json` 中 swarm gate `3/3` 通过，且已有业务输出、runbook 与指标 | `docs/operations/swarm_mvp_operations.zh-CN.md` |

## Gate 与 Smoke 总览

### 最新 gate 状态

| Gate | 当前结果 | 来源 |
| --- | --- | --- |
| office gate | 通过 `20/20` | `artifacts/evals/regression-summary.json` |
| research gate | 通过 `6/6` | `artifacts/evals/research-gate-summary.json` |
| swarm gate | 通过 `3/3` | `artifacts/evals/swarm-gate-summary.json` |

### Smoke Matrix 摘要

| Smoke 层级 | 当前状态 | 入口 | 目的 | 默认使用场景 |
| --- | --- | --- | --- | --- |
| baseline smoke | 已在当前维护的本地检查集中验证 | `python scripts/demo_minimal_agent_os.py --check` | 验证 kernel/runtime 最小可用路径 | CI |
| module smoke | 已在当前维护的本地检查集中验证 | `python scripts/demo_research_module.py --check` | 验证 `research_module` 端到端路径 | CI |
| swarm smoke | 已在当前维护的本地检查集中验证 | `python scripts/demo_research_swarm.py --check` | 验证 research Swarm 端到端路径 | CI |
| release smoke | 仅发布/迁移前使用，不进入默认 CI | `/api/kernel/shadow/smoke`、`/api/kernel/shadow/contracts`、`/api/kernel/shadow/replay` | 迁移/发布前验证 | 发布前 |

Smoke 分层契约见：`docs/operations/smoke_matrix.zh-CN.md`

## 指标总览

### Research Module 指标

最新快照来自 `artifacts/platform_metrics/latest.json`：

- gate case 数：`6`
- 平均 source 数：`1.5`
- fetch 成功率：`0.8`
- evidence 完整度：`complete=2`、`partial=1`、`insufficient=3`
- degraded 响应数：`2`
- empty result 数：`1`
- conflict detected 数：`1`
- 结果等级分布：`success=1`、`degraded=2`、`insufficient_evidence=3`

解释：

- 这个模块已经可以运营，但当前 gate 集仍然刻意覆盖弱证据和降级场景
- empty / insufficient 结果是被显式暴露出来的，而不是被隐藏成“成功”

### Swarm 指标

最新快照来自 `artifacts/platform_metrics/latest.json`：

- gate case 数：`3`
- business output 存在数：`3`
- 平均 branch 数：`3.0`
- merged finding 数：`avg=2.667`、`min=2`、`max=3`
- degraded 运行数：`2`
- failed branch 数：`0`
- conflict detected 数：`1`
- 结果等级分布：`success=1`、`degraded=1`、`insufficient_evidence=1`
- 返回策略分布：`deliver_swarm_summary=1`、`return_swarm_summary_with_caveat=1`、`report_swarm_unreliable_and_offer_refine_or_escalate=1`

解释：

- Swarm 不只是能跑“干净成功”，也已经在 gate 覆盖里验证了降级与冲突场景
- `business_output_present_count == gate_case_count` 说明每个 gated case 都带有业务可读输出

## Replay Sample 库概览

Replay sample 根目录：`evals/replay_samples/`

| 基线类型 | 样本数量 | 当前样本 |
| --- | --- | --- |
| office | `1` | `office_attachment_followup.json` |
| research | `2` | `research_normal_top_fetch.json`、`research_fetch_failure.json` |
| swarm | `2` | `swarm_fanout_merge.json`、`swarm_serial_replay_conflict.json` |

适用场景：

- 把稳定场景升级成后续 gate case
- 在发布前回归中复用固定输入，不再临时拼请求
- 向非开发者解释 office / research / swarm 各自的代表性场景

样本库契约见：`evals/replay_samples/README.md`

## 统一入口索引

### Demo 入口

- baseline demo：`python scripts/demo_minimal_agent_os.py --check`
- research demo：`python scripts/demo_research_module.py --check`
- swarm demo：`python scripts/demo_research_swarm.py --check`

### Gate 入口

- office gate：`python scripts/run_evals.py --cases evals/gate_cases.json --output artifacts/evals/regression-summary.json`
- research gate：`python scripts/run_evals.py --cases evals/research_gate_cases.json --output artifacts/evals/research-gate-summary.json`
- swarm gate：`python scripts/run_evals.py --cases evals/swarm_gate_cases.json --output artifacts/evals/swarm-gate-summary.json`

### Smoke / Replay / Runbook / Docs 入口

- smoke matrix：`docs/operations/smoke_matrix.zh-CN.md`
- replay sample 库：`evals/replay_samples/README.md`
- research 运营文档：`docs/operations/research_module_operations.zh-CN.md`
- Swarm 运营文档：`docs/operations/swarm_mvp_operations.zh-CN.md`
- Swarm runbook：`docs/operations/swarm_mvp_runbook.zh-CN.md`
- gate 策略：`docs/operations/quality_gates.zh-CN.md`
- 指标定义：`docs/operations/platform_metrics.md`

## 汇报入口

固定汇报模板：`docs/operations/platform_reporting_template.zh-CN.md`

这个模板统一了：

- 当前阶段
- 本轮状态
- 风险
- 阻塞
- 下一步

## 数据来源说明

本总览只汇总以下现有来源：

- `artifacts/evals/regression-summary.json`
- `artifacts/evals/research-gate-summary.json`
- `artifacts/evals/swarm-gate-summary.json`
- `artifacts/platform_metrics/latest.json`
- `docs/operations/smoke_matrix.md`
- `evals/replay_samples/README.md`
- `docs/operations/research_module_operations.md`
- `docs/operations/swarm_mvp_operations.md`
- `docs/operations/swarm_mvp_runbook.md`
