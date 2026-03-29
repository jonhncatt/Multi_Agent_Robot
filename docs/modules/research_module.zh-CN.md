# Research Module

English version: [research_module.md](/Users/dalizhou/Desktop/new_validation_agent/docs/modules/research_module.md)

`research_module` 是第二正式业务模块候选，也是当前默认推荐的第一个非 office 正式模块。

## 目标

提供一个干净的、面向 research 的模块，它可以：

- 接受一个聚焦的 investigation query
- 通过正式 tool/provider contract 收集来源
- 在需要时抓取 top source 做证据预览
- 在不经过 `office_module` 的情况下返回结构化摘要
- 把返回结果分成 `success`、`degraded`、`insufficient_evidence`、`failed`

## 正式入口

- [module.py](/Users/dalizhou/Desktop/new_validation_agent/app/business_modules/research_module/module.py)
- [manifest.py](/Users/dalizhou/Desktop/new_validation_agent/app/business_modules/research_module/manifest.py)
- [module.json](/Users/dalizhou/Desktop/new_validation_agent/app/business_modules/research_module/module.json)

## 当前流水线

```text
KernelHost.dispatch(TaskRequest)
  -> research_module.handle(...)
  -> tool_runtime_module.execute(web.search)
  -> optional tool_runtime_module.execute(web.fetch)
  -> structured research summary
```

```text
KernelHost.dispatch(TaskRequest)
  -> research_module.handle(...)
  -> parallel research branches
  -> serial replay for failed branch
  -> Aggregator (merge / deduplicate / mark conflicts)
  -> Swarm research summary + trace
```

## Tool Contract 使用

当前必需工具：

- `web.search`
- `web.fetch`

未来可选工具：

- `file.read`
- `workspace.read`

模块不能直接调用 provider。

## 独立 Demo 要求

只有当它能在不依赖 `office_module` 的前提下独立演示时，这个模块才算是有效的第二正式模块。

运行：

```bash
python scripts/demo_research_module.py --check
```

这个 demo 会通过 `KernelHost` 运行 `research_module`，并使用确定性的 provider stub。

## 运营标准

关于结果等级、降级策略和升级规则的运营说明见：

- [research_module_operations.zh-CN.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/research_module_operations.zh-CN.md)

## Swarm MVP Demo

`M5` 把 `research_module` 扩展成一个边界收窄的模块内 Swarm 模式。

运行：

```bash
python scripts/demo_research_swarm.py --check
```

这个 demo 证明：

- 多个 research 输入可以并行处理
- branch 失败会通过 `serial_replay` 降级恢复
- Aggregator 只做 merge、deduplicate、mark conflicts
- Swarm payload 暴露业务可读输出块：
  - `overall_summary`
  - `per_branch_evidence`
  - `conflict_and_degradation_notes`
- trace 暴露 `swarm_branch_plan`、`swarm_degradation`、`swarm_join`

相关阅读：

- [research_swarm_demo.md](/Users/dalizhou/Desktop/new_validation_agent/docs/demo/research_swarm_demo.md)
- [swarm_mvp_operations.zh-CN.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/swarm_mvp_operations.zh-CN.md)
- [swarm_mvp_runbook.zh-CN.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/swarm_mvp_runbook.zh-CN.md)
