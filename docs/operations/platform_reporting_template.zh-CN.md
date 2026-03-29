# 平台汇报模板

这个模板用于项目汇报、运营汇报或里程碑汇报。保持简短，内容从当前总览、eval artifacts、metrics 和 runbook 中直接填写。

English version: [platform_reporting_template.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/platform_reporting_template.md)

## 模板

### 当前阶段

- 阶段：
- 当前目标：

### 本轮状态

- office baseline：
- research_module：
- Swarm MVP：
- gates：
- smoke：
- replay sample 库：

### 风险

- 风险 1：
- 风险 2：

### 阻塞

- 阻塞 1：
- 阻塞 2：

### 下一步

- 下一步 1：
- 下一步 2：

## 填写规则

- gate 数字直接引用 `artifacts/evals/*.json`
- research 和 Swarm 指标直接引用 `artifacts/platform_metrics/latest.json`
- 默认先看 `docs/operations/platform_operations_overview.zh-CN.md`，再决定是否下钻到更细文档
- 只有在对应 gate 或 smoke 确实通过时，才称为“绿色”
- 如果结果是 `degraded` 或 `insufficient_evidence`，要直说，不要折叠成 `success`
