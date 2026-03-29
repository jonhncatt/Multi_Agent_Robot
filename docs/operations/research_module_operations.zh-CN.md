# Research Module 运营说明

English version: [research_module_operations.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/research_module_operations.md)

## 这个模块是做什么的

`research_module` 是第二正式业务模块。它的职责刻意收窄：

- 为一个聚焦 research query 搜集来源
- 在需要时抓取 top source 做证据预览
- 返回边界清楚、可解释的摘要
- 在证据弱或不完整时保守降级

它不应该：

- 瞎猜
- 在冲突证据上强行裁决
- 把降级的证据质量悄悄藏起来

## 结果等级

### `success`

适用条件：

- 至少拿到两个可用来源
- 没检测到冲突的 top-source 标题
- 没触发 provider fallback
- 可以直接返回答案

返回策略：

- `deliver_answer`

### `degraded`

适用条件：

- 结果仍然可用
- 但执行路径发生了降级，例如：
  - top-source fetch 失败
  - 需要 provider fallback
  - 证据不完整但仍有可服务内容

返回策略：

- `return_search_only_with_caveat`
- `return_answer_with_provider_fallback_note`

运营要求：

- 不能隐藏 caveat
- 可以继续返回答案，但必须明确 reliability note

### `insufficient_evidence`

适用条件：

- 没找到可用来源
- 只找到一个可用来源
- top sources 冲突，模块无法安全裁决

返回策略：

- `ask_rewrite_query`
- `report_unreliable_and_offer_swarm`

运营要求：

- 不要把它包装成有把握的事实答案
- 要明确告诉用户证据弱或存在冲突
- 主题太宽时建议缩窄 query，或升级到 Swarm

### `failed`

适用条件：

- search 还没拿到任何可用证据就失败
- tool runtime 不可用
- 所有 provider 路径都失败，无法产出结果

返回策略：

- `report_failure`

运营要求：

- 明确失败
- 不要伪装成 degraded success

## 什么情况下算成功

从运营角度看，`research_module` 算成功，当且仅当：

- 返回 `success` 或 `degraded`
- 返回文本与证据质量一致
- payload 明确记录 result grade、return strategy 和 evidence completeness

`insufficient_evidence` 不是执行崩溃，但也不算可靠的证据答案。应视为“被正确处理，但结果不可靠”。

## 什么时候降级

以下情况应降级而不是失败：

- search 成功但 fetch 失败
- provider fallback 把请求救回来了
- 模块仍能返回有边界的答案，并附带明确 caveat

## 什么时候提示用户改写 query

以下情况应建议用户改写或收窄 query：

- 0 个可用来源
- 请求太宽，只能得到一个弱来源
- 当前措辞过于模糊，无法稳定取证

## 什么时候明确说“证据不足 / 结果不可靠”

以下情况必须直说：

- 只有 1 个可用来源
- top sources 互相冲突
- 模块无法负责地把分歧压成一个答案

## 什么时候交给 Swarm 或更高层能力

以下情况适合升级到 Swarm 或更高层研究流：

- 主题天然可以拆成多个子问题
- 单 query 路径持续返回 `insufficient_evidence`
- 冲突需要并行收集证据，而不是单源回答

不要对所有 degraded case 自动升级。单纯的 fetch 失败或 provider fallback 还不足以触发 Swarm。

## 运营指标

当前指标输出到 `artifacts/platform_metrics/latest.json` 的 `research_module` 字段下。

至少关注：

- `source_count`
- `fetch_success_rate`
- `evidence_completeness`
- `degraded_response_count`
- `empty_result_count`
- `conflict_detected_count`

解释口径：

- `empty_result_count` 上升，说明 query 质量或 provider 覆盖在下滑
- `degraded_response_count` 上升，说明模块更频繁地靠 fallback 或不完整证据维持可用
- `conflict_detected_count` 非零，说明模块正在显式暴露冲突，而不是偷偷裁决
