# Shim Retirement Scoreboard

## Completed

| Shim | Status | Replacement | Notes |
| --- | --- | --- | --- |
| `app/router_rules.py` | Retired | `packages/office_modules/router_hints.py` | Removed from runtime imports and guarded by the platform-boundary check |

## Remaining Active Shims

| Shim | Current Role | Next Retirement Dependency |
| --- | --- | --- |
| `app/agent.py` | Legacy Office runtime shim | `office_module` must stop delegating to `OfficeAgent` |
| `packages/runtime_core/kernel_host.py` | Legacy capability host shim | debug/eval paths must stop depending on capability-runtime host snapshots |
| `app/request_analysis_support.py` | Request-analysis helper shim | office request analysis must move behind module-scoped helpers |
| `app/router_intent_support.py` | Router helper shim | office intent helper logic must move behind module-scoped routing helpers |
| `app/execution_policy.py` | Execution-policy lookup shim | policy definitions must move into contract-scoped or module-local registries |
