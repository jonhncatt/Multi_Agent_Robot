# Swarm MVP 运营说明

English version: [swarm_mvp_operations.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/swarm_mvp_operations.md)

## 这个流程是做什么的

`research_module` 的 Swarm MVP 是一个边界收窄的多 branch research 流程。

它的职责是：

- 把一个较宽的 research 请求拆成明确的 branch 输入
- 让每个 branch 走现有 research 路径
- 对失败 branch 使用 `serial_replay` 恢复
- 合并可用证据
- 标记冲突，而不是强行裁决
- 返回业务可读的结果，并解释置信度和降级原因

它不应该：

- 变成 kernel 级 scheduler
- 把 branch 失败包装成假的“成功”
- 覆盖冲突证据
- 扮演智能裁判

## 结果等级

### `success`

适用条件：

- 最终 merge 至少得到两个可用 finding
- 降级处理结束后没有残留 failed branch
- 最终证据里没有冲突标记
- 没有走 degraded recovery

返回策略：

- `deliver_swarm_summary`

运营要求：

- 可以作为默认多分支结果展示
- 不需要额外 caveat

### `degraded`

适用条件：

- 最终 merge 仍然可用
- 至少一个 branch 走了 degraded recovery
- 最终证据没有残留冲突

返回策略：

- `return_swarm_summary_with_caveat`

运营要求：

- 继续保留整体结果
- 明确指出哪个 branch 降级了
- 解释为什么结果仍然可用

### `insufficient_evidence`

适用条件：

- branch 之间仍存在冲突
- 或最终 merge 太薄，不能支撑有把握的结果

返回策略：

- `report_swarm_unreliable_and_offer_refine_or_escalate`

运营要求：

- 不要把输出包装成确定答案
- 明确说明冲突或证据缺口
- 建议 refine 输入，或升级到更高层流程

### `failed`

适用条件：

- 降级处理之后仍有 branch 失败
- 或无法形成稳定的最终 merge

返回策略：

- `report_swarm_failure`

运营要求：

- 明确失败
- 不要包装成 degraded success

## 什么情况下算运营成功

从运营视角看，Swarm MVP 算成功，当且仅当：

- 返回 `success` 或 `degraded`
- 业务输出里有完整三层：
  - `overall_summary`
  - `per_branch_evidence`
  - `conflict_and_degradation_notes`
- 结果能清楚解释 merge 参与情况、冲突状态和可靠性

`insufficient_evidence` 是被正确处理的输出，不是执行崩溃，但也不是可放心对外的成功态。

## 指标

Swarm 指标输出到 `artifacts/platform_metrics/latest.json` 的 `swarm` 字段下。

至少关注：

- `gate_case_count`
- `business_output_present_count`
- `branch_count`
- `merged_finding_count`
- `degraded_run_count`
- `failed_branch_count`
- `conflict_detected_count`
- `result_grade_counts`
- `return_strategy_counts`

解释口径：

- `degraded_run_count` 上升，说明恢复路径被更频繁使用
- `failed_branch_count` 上升，说明 branch 失败开始超出安全降级能力
- `conflict_detected_count` 上升，说明系统在暴露冲突，而不是隐藏冲突
- `business_output_present_count` 应该与 `gate_case_count` 相等；如果不相等，说明业务输出 contract 漂移了

## 什么时候升级处理

以下情况应升级到 Swarm MVP 之上的能力：

- 多次运行仍停留在 `insufficient_evidence`
- 冲突需要人工裁决
- 请求本身需要更宽的 planner 或更复杂的 research workflow

不要对所有 `degraded` 情况自动升级。只要最终 merge 仍然连贯，恢复后的 branch 仍属于可接受的 Swarm 结果。
