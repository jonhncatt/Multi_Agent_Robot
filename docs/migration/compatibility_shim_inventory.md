# Compatibility Shim Inventory

This file tracks every active compatibility shim as a managed migration object.

## Active Inventory

| Path | Current Role | Why It Still Exists | Known Dependents | Retirement Condition |
| --- | --- | --- | --- | --- |
| `app/agent.py` | Legacy Office runtime and compatibility orchestration shim | `office_module` still delegates to `OfficeAgent` for the main office execution path | `app/business_modules/office_module/module.py`, router-layer tests, runtime debug paths | `office_module` runs its own pipeline end to end without `OfficeAgent` delegation |
| `packages/runtime_core/kernel_host.py` | Legacy host compatibility surface | debug, eval, and compatibility runtime paths still depend on the legacy host object model | `app/main.py`, `app/evals.py`, bootstrap legacy host wiring | Agent OS runtime surfaces fully replace legacy host snapshots and lifecycle hooks |
| `app/request_analysis_support.py` | Request-analysis helper shim | legacy office runtime still imports request analysis helpers during compatibility execution | `app/agent.py` and related office runtime paths | request-analysis helpers move behind module-scoped packages and no runtime imports remain |
| `app/router_intent_support.py` | Router helper shim | legacy office runtime still uses intent support helpers and normalization behavior | `app/agent.py` and router compatibility tests | intent support logic lives behind module-scoped routing packages only |
| `app/execution_policy.py` | Execution-policy lookup shim | compatibility runtime and route normalization still reference policy names here | `app/agent.py`, route normalization, migration tests | formal policy definitions live only behind module-local or contract-scoped registries |

## Retired Shims

| Path | Retirement Outcome | Replacement | Retirement Proof |
| --- | --- | --- | --- |
| `app/router_rules.py` | Removed from the runtime path and deleted from the repository | `packages/office_modules/router_hints.py` | runtime imports now point at `packages/office_modules/router_hints.py`; boundary gate rejects new `app.router_rules` imports |

## Operating Rules

- A shim may forward, normalize, or preserve compatibility.
- A shim may not become the long-term owner of new business capability.
- Any shim change must update this inventory and `docs/migration/deprecation_plan.md`.
- A retired shim must not be reintroduced through new runtime imports.
- A shim is not considered retired until tests and integration paths pass without importing it from the main execution path.
