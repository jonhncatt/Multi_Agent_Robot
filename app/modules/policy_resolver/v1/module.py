from __future__ import annotations

from typing import Any


class PolicyResolverModule:
    module_id = "policy_resolver"
    version = "1.0.0"

    def normalize_route(
        self,
        *,
        agent: Any,
        route: dict[str, Any],
        fallback: dict[str, Any],
        settings: Any,
    ) -> dict[str, Any]:
        return agent._normalize_route_decision_impl(route=route, fallback=fallback, settings=settings)
