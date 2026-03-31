from __future__ import annotations

import asyncio

from app.kernel.host import KernelHost
from app.kernel.llm_router import LLMRouter


def test_llm_router_discovers_independent_agents() -> None:
    host = KernelHost()
    router = LLMRouter(host)
    result = asyncio.run(router.discover_agents(force=True))

    assert bool(result.get("ok")) is True
    assert int(result.get("count") or 0) >= 12
    assert "worker_agent" in router.agents
    assert "planner_agent" in router.agents


def test_llm_router_reload_not_found_agent() -> None:
    host = KernelHost()
    router = LLMRouter(host)
    asyncio.run(router.discover_agents(force=True))
    result = asyncio.run(router.reload_single_agent("missing_agent"))
    assert bool(result.get("ok")) is False


def test_llm_router_route_fallback_when_llm_unavailable(monkeypatch) -> None:
    host = KernelHost()
    router = LLMRouter(host)
    asyncio.run(router.discover_agents(force=True))

    async def _fake_json_completion(**kwargs):
        return {"ok": False, "error": "forced"}

    monkeypatch.setattr(router, "_json_completion", _fake_json_completion)
    plan = asyncio.run(router.route("请帮我规划下周研发任务"))

    assert isinstance(plan.get("steps"), list)
    assert len(plan.get("steps") or []) >= 1


def test_llm_router_execute_runs_agent_step() -> None:
    host = KernelHost()
    router = LLMRouter(host)
    host.attach_llm_router(router)
    asyncio.run(router.discover_agents(force=True))
    plan = {
        "plan": "unit_test",
        "parallel": False,
        "steps": [{"agent": "worker_agent", "task": "生成一段简短总结"}],
    }
    result = asyncio.run(router.execute(plan))

    rows = list(result.get("results") or [])
    assert len(rows) == 1
    assert str(rows[0].get("status")) == "success"

