# Kernel Contract

## Responsibility

`KernelHost` is the stable kernel orchestration layer.

It is responsible for:

- loading modules
- resolving a business module for a request
- performing platform-level module selection when the caller does not explicitly pin a module
- injecting tool/provider access through registries
- running the selected module in isolation
- collecting health and runtime traces
- falling back or rolling back when a module/provider degrades

It must not own:

- office-specific prompt logic
- Router / Planner / Worker / Reviewer / Revision role prompts
- office-specific heuristics
- business-domain rules

## Module Selection

Selection precedence is fixed:

1. explicit `module_id`
2. explicit module task types such as `task.office`, `task.research`, `task.coding`, `task.adaptation`
3. intelligent selection for generic chat requests such as `chat` / `task.chat`

Current intelligent selection scope is intentionally narrow:

- `office_module`
- `research_module`

These are the only modules that are currently auto-routable for generic chat traffic.
`coding_module` and `adaptation_module` remain explicit-only until they stop being skeleton modules and report healthy operational status.

The selector may use:

- request text
- request attachments
- request context hints such as `research_query` or `swarm_inputs`
- module health/readiness from registry state

The selector must not:

- move office internal routing into the kernel
- turn Swarm into a kernel planner
- auto-route into unhealthy or skeleton business modules

## Lifecycle

Supported lifecycle states for modules:

- `init`
- `ready`
- `degraded`
- `disabled`
- `rollback`

## Health

- Every module must expose `health_check()`.
- Every provider must expose `health_check()`.
- Startup runs a health pass and records status in registry state.
- A failed module invocation degrades the module without crashing the kernel.
- Provider repeated failures can open a simple circuit and force fallback.

## Public Surface

- `load_modules()`
- `select_module(request, module_id=None)`
- `resolve_module(request)`
- `inject_tools_and_providers(module)`
- `run_module(module, request, context)`
- `observe_and_record(trace)`
- `fallback_or_rollback(module_id)`
- `dispatch(request, module_id=None)`
