# 质量门禁

English version: [quality_gates.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/quality_gates.md)

## 策略

仓库当前把以下几层视为正式门禁：

- `tests/`：contract 与 regression 安全线
- `evals/`：office baseline、research module、Swarm 行为门禁
- `docs/operations/smoke_matrix.md`：smoke 分层契约
- `evals/replay_samples/`：轻量 replay 样本库，用于回归种子
- `scripts/check_platform_boundaries.py`：平台边界与兼容层保护
- `scripts/collect_platform_metrics.py`：平台指标 artifact 生成
- `.github/workflows/regression-ci.yml`：push / PR 分支门禁

## 命令

安装开发依赖：

```bash
pip install -r requirements-dev.txt
```

本地完整门禁：

```bash
python scripts/check_platform_boundaries.py --base origin/main
python scripts/collect_platform_metrics.py
pytest -q tests
python scripts/run_evals.py --cases evals/gate_cases.json --output artifacts/evals/regression-summary.json
python scripts/run_evals.py --cases evals/research_gate_cases.json --output artifacts/evals/research-gate-summary.json
python scripts/run_evals.py --cases evals/swarm_gate_cases.json --output artifacts/evals/swarm-gate-summary.json
python scripts/demo_minimal_agent_os.py --check
python scripts/demo_research_module.py --check
python scripts/demo_research_swarm.py --check
```

## 不同改动该跑哪些门禁

- 模块 contract 变更：`pytest -q tests/kernel tests/modules tests/migration`
- office / router 行为变更：`pytest -q tests/router` 加 `python scripts/run_evals.py --cases evals/gate_cases.json`
- research_module 变更：`python scripts/run_evals.py --cases evals/research_gate_cases.json` 加 `python scripts/demo_research_module.py --check`
- Swarm MVP 变更：`python scripts/run_evals.py --cases evals/swarm_gate_cases.json` 加 `python scripts/demo_research_swarm.py --check`
- tool / provider 变更：`pytest -q tests/tool_providers tests/integration`
- 打包或兼容层变更：`pytest -q tests/migration`
- shim 变更：`python scripts/check_platform_boundaries.py --base origin/main`
- 里程碑或运营层变更：`python scripts/collect_platform_metrics.py`

如果要跑更大的探索回归，再单独使用 `evals/cases.json`。

配套入口：

- smoke 分层：`docs/operations/smoke_matrix.zh-CN.md`
- replay 样本库：`evals/replay_samples/README.md`
- 单一运营入口：`docs/operations/platform_operations_overview.zh-CN.md`
- 固定汇报模板：`docs/operations/platform_reporting_template.zh-CN.md`

## CI 行为

当前 [`regression-ci.yml`](/Users/dalizhou/Desktop/new_validation_agent/.github/workflows/regression-ci.yml) 会检查：

- 平台边界保护
- 平台指标 artifact
- Python 可编译性
- 前端脚本语法
- 全量 pytest
- baseline smoke
- module smoke
- Swarm smoke
- office baseline eval gate
- research-module eval gate
- Swarm eval gate

这些项目没有全部为绿时，不应视为安全合并。
