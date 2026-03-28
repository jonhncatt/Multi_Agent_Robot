# Current Execution Path

## Canonical Path

```text
HTTP / UI
  -> app/main.py
  -> app/bootstrap/assemble.py
  -> app/kernel/host.py::KernelHost.dispatch(TaskRequest)
  -> app/business_modules/office_module/module.py::OfficeModule.handle(...)
  -> packages/office_modules/office_agent_runtime.py::OfficeAgent
  -> ToolRegistry / ProviderRegistry / ToolBus
  -> TaskResponse + Kernel trace
```

## Notes

- The external business entry is `KernelHost.dispatch(...)`.
- `office_module` is the only formal business module used by the current chat path.
- `app/main.py` still owns HTTP/session/attachment lifecycle.
- `app/core/*` still owns manifest-based kernel modules for router/policy/attachment/finalizer in the legacy runtime.

## Deprecated Or Compatibility Paths

- `app/agent.py`
  - Status: retired runtime shim placeholder
  - Why: retained only as a compatibility re-export while external references are cleaned up

## Retired Compatibility Paths

- `packages/runtime_core/kernel_host.py`
  - Status: retired
  - Replacement: `AgentOSRuntime` explicit legacy facade/helper bindings plus `packages/runtime_core/legacy_host_support.py`
- `app/execution_policy.py`
  - Status: retired
  - Replacement: `packages/office_modules/execution_policy.py`
- `app/router_rules.py`
  - Status: retired
  - Replacement: `packages/office_modules/router_hints.py`
- `app/request_analysis_support.py`
  - Status: retired
  - Replacement: `packages/office_modules/request_analysis.py`
- `app/router_intent_support.py`
  - Status: retired
  - Replacement: `packages/office_modules/intent_support.py`

## Compatibility Shims

- none

## Planned Removal Order

1. Remove any remaining external imports of `app.agent`
2. Delete the temporary `app/agent.py` placeholder
