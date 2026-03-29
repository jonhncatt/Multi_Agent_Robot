# Swarm MVP Demo And Release Runbook

中文版本: [swarm_mvp_runbook.zh-CN.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/swarm_mvp_runbook.zh-CN.md)


## Purpose

Use this runbook before:

- showing the Swarm MVP to non-developers
- promoting Swarm changes through CI
- validating a release candidate or migration candidate

This runbook does not add new product behavior. It validates that the current bounded Swarm contract is still intact.

## Demo Checklist

Run:

```bash
python scripts/demo_research_swarm.py --check
```

For a readable walkthrough, run:

```bash
python scripts/demo_research_swarm.py
```

Confirm that the output shows:

- `overall_summary`
- `per_branch_evidence`
- `conflict_and_degradation_notes`

For each branch, confirm that you can explain:

- what the branch was about
- whether it succeeded, degraded, or failed
- how much evidence it produced
- whether it contributed to the final merge

## CI / Gate Checklist

Run:

```bash
pytest -q tests
python scripts/run_evals.py --cases evals/swarm_gate_cases.json --output artifacts/evals/swarm-gate-summary.json
python scripts/demo_research_swarm.py --check
python scripts/check_platform_boundaries.py --base origin/main
python scripts/collect_platform_metrics.py
```

Treat the run as blocked if:

- Swarm gate cases do not pass
- the demo smoke fails
- `business_output` is missing from any Swarm gate artifact
- `result_grade_counts` or `return_strategy_counts` disappear from platform metrics

## Release-Prep Checklist

Before release or migration validation, also run:

```bash
/api/kernel/shadow/smoke
/api/kernel/shadow/contracts
/api/kernel/shadow/replay
```

Use these only for release or migration workflows, not as default branch-gate checks.

## Result Interpretation

- `success`
  - release/demo can proceed
  - no special caveat is required
- `degraded`
  - release/demo can proceed with an explicit caveat
  - call out the degraded branch and recovery reason
- `insufficient_evidence`
  - do not present as a confident final answer
  - present conflict or evidence gaps clearly
  - consider refining inputs before release/demo
- `failed`
  - stop
  - do not promote the build as a stable Swarm run

## Required Artifacts

Keep these available for review:

- `artifacts/evals/swarm-gate-summary.json`
- `artifacts/platform_metrics/latest.json`
- `docs/operations/swarm_mvp_operations.md`
- `docs/operations/smoke_matrix.md`

## Stop Conditions

Do not promote or demo as healthy if any of these occur:

- a branch still fails after `serial_replay`
- the final merge has no usable findings
- the business output contract is missing
- the final output cannot explain conflict or degradation in plain language
