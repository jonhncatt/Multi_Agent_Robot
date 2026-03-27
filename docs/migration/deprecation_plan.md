# Deprecation Plan

## Active Compatibility Layers

- `app/agent.py`
- `packages/runtime_core/kernel_host.py`
- `app/request_analysis_support.py`
- `app/router_intent_support.py`
- `app/execution_policy.py`

## Completed Retirements

- `app/router_rules.py`
  - Replaced by `packages/office_modules/router_hints.py`
  - Removed from the runtime import path
  - Protected by the platform-boundary gate so legacy imports fail review

## Deletion Conditions

- `office_module` no longer delegates to `OfficeAgent`
- main request path no longer needs capability-runtime host objects for health/debug
- office routing/policy helpers fully live behind module-scoped packages
- integration tests pass without importing compatibility helpers

## Sequence

1. migrate office runtime internals into `app/business_modules/office_module/*`
2. sever `office_module -> OfficeAgent` delegation
3. retire legacy capability host coupling
4. remove remaining helper shims
