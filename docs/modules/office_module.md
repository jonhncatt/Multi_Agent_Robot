# Office Module

## Responsibility

`office_module` is the formal office business module.

It owns:

- the office request boundary
- the internal role pipeline contract
- module manifest / health / rollback metadata
- declared tool requirements
- delegation to the canonical office runtime implementation under `packages/office_modules/*`

It must not be treated as:

- the kernel
- a top-level system module
- a direct provider caller

## Internal Pipeline

Declared role chain:

- `router`
- `planner`
- `worker`
- `reviewer`
- `revision`

Current runtime note:

- `office_module.handle(...)` is the formal entrypoint
- execution now delegates to `packages.office_modules.office_agent_runtime.OfficeAgent`
- the old `app.agent` path is retired from the runtime path

## Tools And Providers

Required tools:

- `workspace.read`
- `file.read`
- `web.search`
- `write.patch`

Optional tools:

- `workspace.write`
- `web.fetch`
- `code.search`
- `session.lookup`

## Kernel Interaction

- `KernelHost.dispatch(...)` resolves `office_module`
- Kernel injects registry context and provider visibility
- Tool/provider selection is recorded in the kernel trace

Reference docs:

- [Module Integration Guide](/Users/dalizhou/Desktop/new_validation_agent/docs/modules/module_integration_guide.md)
- [Minimal Demo](/Users/dalizhou/Desktop/new_validation_agent/docs/demo/minimal_demo.md)
