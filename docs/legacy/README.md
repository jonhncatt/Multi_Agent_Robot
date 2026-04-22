# Legacy Compatibility Surface

This repository is migrating toward a chat-product-only runtime.

The following areas are now considered **legacy compatibility surfaces** rather than the primary product path:

- `app/bootstrap/`
- kernel / research / swarm demo scripts
- migration and compatibility shim tests
- platform-only smoke and eval gates

Current production-facing work should target the chat product path:

- `app/main.py`
- `app/vintage_programmer_runtime.py`
- `app/local_tools.py`
- `app/static/*`

During the transition:

- the chat product starts through a dedicated chat runtime surface
- historical AgentOS assembly is resolved lazily through a legacy boundary
- legacy smoke and eval flows remain available for internal validation, but are no longer the primary release gate for chat product changes
