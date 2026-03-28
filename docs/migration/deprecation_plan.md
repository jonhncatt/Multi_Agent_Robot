# Deprecation Plan

## Active Compatibility Layers

- none

## Completed Retirements

- `app/agent.py`
  - Replaced by `packages/office_modules/office_agent_runtime.py` plus canonical office factory wiring
  - Removed from the runtime import path; retained only as a compatibility re-export placeholder
  - Protected by the platform-boundary gate so new `app.agent` imports fail review
- `packages/runtime_core/kernel_host.py`
  - Replaced by explicit `AgentOSRuntime` legacy facade/helper bindings plus `packages/runtime_core/legacy_host_support.py`
  - Removed from runtime assembly and deleted from the repository
  - Protected by the platform-boundary gate so legacy imports fail review
- `app/execution_policy.py`
  - Replaced by `packages/office_modules/execution_policy.py`
  - Removed from the runtime import path
  - Protected by the platform-boundary gate so legacy imports fail review
- `app/router_rules.py`
  - Replaced by `packages/office_modules/router_hints.py`
  - Removed from the runtime import path
  - Protected by the platform-boundary gate so legacy imports fail review
- `app/request_analysis_support.py`
  - Replaced by `packages/office_modules/request_analysis.py`
  - Removed from the runtime import path
  - Protected by the platform-boundary gate so legacy imports fail review
- `app/router_intent_support.py`
  - Replaced by `packages/office_modules/intent_support.py`
  - Removed from the runtime import path
  - Protected by the platform-boundary gate so legacy imports fail review

## Deletion Conditions

- the temporary `app/agent.py` re-export placeholder has no external consumers
- office routing/policy/helpers remain behind module-scoped packages
- integration tests continue to pass without importing `app.agent` from the runtime path

Status:

- `app/agent.py`: retired from the runtime path; placeholder remains only for compatibility imports
- `packages/runtime_core/kernel_host.py`: retired
- runtime-path host instantiation: removed in favor of explicit facade/helper bindings
- `get_legacy_host()`: no longer part of runtime behavior; retained only as a compatibility accessor entrypoint
- blackboard orchestration: remains externalized in `packages/runtime_core/legacy_host_support.py`
- remaining active shim focus: none
- `OfficeExecutionEngine`: canonical office runtime entry now delegates into `packages.office_modules.office_agent_runtime.OfficeAgent`

## Sequence

1. move the main office execution path behind `OfficeExecutionEngine`
2. migrate module wrappers off runtime-private methods
3. migrate shadow / smoke / replay / worker / eval helper consumers to explicit runtime/helper surfaces
4. remove the `packages/office_modules/agent_module.py -> app.agent` direct import
5. delete the temporary `app/agent.py` re-export placeholder once no external consumers remain
