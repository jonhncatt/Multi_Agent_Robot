from __future__ import annotations

from typing import Any


class BaseIndependentAgent:
    """
    极简独立 Agent 基类：
    - 每个 Agent 只有 name/description/capabilities
    - 统一入口 handle_task
    - 真正的推理由 kernel.llm_router.agent_reason 执行
    """

    def __init__(
        self,
        *,
        name: str,
        description: str,
        capabilities: list[str] | tuple[str, ...],
        kernel: Any | None = None,
    ) -> None:
        self.name = str(name or "").strip()
        self.description = str(description or "").strip()
        self.capabilities = [str(item).strip() for item in list(capabilities or []) if str(item).strip()]
        self.kernel = kernel

    async def handle_task(self, task: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(task, str):
            payload: dict[str, Any] = {"query": task}
        else:
            payload = dict(task or {})
        query = str(payload.get("query") or payload.get("task") or "").strip()
        if not query:
            query = "请执行该 Agent 的默认职责并返回简洁结果。"

        router = getattr(self.kernel, "llm_router", None) if self.kernel is not None else None
        if router is not None and hasattr(router, "agent_reason"):
            result = await router.agent_reason(
                agent_name=self.name,
                agent_description=self.description,
                capabilities=self.capabilities,
                task=query,
                context=payload.get("context"),
            )
        else:
            result = f"{self.name} 已处理任务：{query}"

        return {
            "agent": self.name,
            "status": "success",
            "result": result,
            "raw_output": result,
        }

