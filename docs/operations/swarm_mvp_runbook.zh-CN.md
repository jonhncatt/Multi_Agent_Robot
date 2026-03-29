# Swarm MVP 演示 / 发布前 Runbook

English version: [swarm_mvp_runbook.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/swarm_mvp_runbook.md)

## 用途

这个 runbook 用于以下场景：

- 向非开发者演示 Swarm MVP 前
- 把 Swarm 相关变更推进 CI 前
- 做发布候选或迁移候选验证前

它不会新增产品行为，只负责验证当前边界收窄的 Swarm contract 仍然完整。

## 演示检查清单

运行：

```bash
python scripts/demo_research_swarm.py --check
```

如果要看可读 walkthrough，运行：

```bash
python scripts/demo_research_swarm.py
```

确认输出里能看到：

- `overall_summary`
- `per_branch_evidence`
- `conflict_and_degradation_notes`

对每个 branch，都要能解释：

- 这个 branch 在研究什么
- 它是成功、降级还是失败
- 它产出了多少证据
- 它是否进入了最终 merge

## CI / Gate 检查清单

运行：

```bash
pytest -q tests
python scripts/run_evals.py --cases evals/swarm_gate_cases.json --output artifacts/evals/swarm-gate-summary.json
python scripts/demo_research_swarm.py --check
python scripts/check_platform_boundaries.py --base origin/main
python scripts/collect_platform_metrics.py
```

以下情况视为阻塞：

- Swarm gate cases 没过
- demo smoke 失败
- 任一 Swarm gate artifact 里缺失 `business_output`
- 平台指标中缺失 `result_grade_counts` 或 `return_strategy_counts`

## 发布前检查清单

发布前或迁移验证前，还要补跑：

```bash
/api/kernel/shadow/smoke
/api/kernel/shadow/contracts
/api/kernel/shadow/replay
```

这些只适用于发布或迁移流程，不进默认分支门禁。

## 结果解释口径

- `success`
  - 可以继续发布 / 演示
  - 不需要额外 caveat
- `degraded`
  - 可以继续发布 / 演示，但必须明确 caveat
  - 需要指出降级 branch 和恢复原因
- `insufficient_evidence`
  - 不应作为有把握的最终答案展示
  - 必须清楚说明冲突或证据缺口
  - 演示 / 发布前应考虑 refine 输入
- `failed`
  - 立即停止
  - 不要把当前版本当作稳定 Swarm 输出对外展示

## 必要 artifact

至少保留以下材料：

- `artifacts/evals/swarm-gate-summary.json`
- `artifacts/platform_metrics/latest.json`
- `docs/operations/swarm_mvp_operations.zh-CN.md`
- `docs/operations/smoke_matrix.zh-CN.md`

## Stop Conditions

出现以下任一情况时，不应继续以“健康 Swarm”名义演示或发布：

- `serial_replay` 之后仍有 branch 失败
- 最终 merge 没有可用 finding
- 缺失业务输出 contract
- 最终输出无法用通俗语言解释冲突或降级
