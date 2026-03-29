# Smoke Matrix

中文版本: [smoke_matrix.zh-CN.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/smoke_matrix.zh-CN.md)


| Layer | Entry | Purpose | CI | When to Run |
| --- | --- | --- | --- | --- |
| baseline smoke | `python scripts/demo_minimal_agent_os.py --check` | Verify the kernel/runtime baseline still boots and returns a healthy minimal path. | yes | every push / PR |
| module smoke | `python scripts/demo_research_module.py --check` | Verify the second formal module still dispatches through `KernelHost` and returns a research result. | yes | every push / PR |
| swarm smoke | `python scripts/demo_research_swarm.py --check` | Verify module-local Swarm fan-out, join, and degradation still run end-to-end. | yes | every push / PR |
| release smoke | `/api/kernel/shadow/smoke`, `/api/kernel/shadow/contracts`, `/api/kernel/shadow/replay` | Verify release or migration candidates against shadow safety checks before promotion. | no | release prep / migration validation |

## Layering Rules

- Baseline smoke guards platform boot and the smallest viable dispatch path.
- Module smoke guards non-office module health and should stay focused on `research_module` until a new formal module exists.
- Swarm smoke guards the current business-facing Swarm MVP, not a future scheduler rewrite.
- Release smoke is heavier and belongs in migration or release workflows, not the default CI branch gate.
