# Shim Retirement Scoreboard

## Completed

| Shim | Status | Replacement | Notes |
| --- | --- | --- | --- |
| `packages/runtime_core/kernel_host.py` | Retired | `AgentOSRuntime` explicit legacy facade/helper bindings plus `packages/runtime_core/legacy_host_support.py` | Runtime assembly no longer instantiates the compatibility host; `get_legacy_host()` now resolves to explicit compatibility accessors and boundary checks reject new `packages.runtime_core.kernel_host` imports |
| `app/agent.py` | Retired from runtime path | `packages/office_modules/office_agent_runtime.py` | Runtime factories no longer import `app.agent`; boundary checks reject new `app.agent` imports; the file remains only as a compatibility re-export placeholder |
| `app/execution_policy.py` | Retired | `packages/office_modules/execution_policy.py` | Removed from runtime imports and guarded by the platform-boundary check |
| `app/router_rules.py` | Retired | `packages/office_modules/router_hints.py` | Removed from runtime imports and guarded by the platform-boundary check |
| `app/request_analysis_support.py` | Retired | `packages/office_modules/request_analysis.py` | Removed from runtime imports and guarded by the platform-boundary check |
| `app/router_intent_support.py` | Retired | `packages/office_modules/intent_support.py` | Removed from runtime imports and guarded by the platform-boundary check |

## Remaining Active Shims

No active shims remain.
