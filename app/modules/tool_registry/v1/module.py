from __future__ import annotations

from typing import Any


class ToolRegistryModule:
    module_id = "tool_registry"
    version = "1.0.0"

    def build_langchain_tools(self, *, agent: Any) -> list[Any]:
        return agent._build_langchain_tools()
