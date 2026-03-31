from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["agents"])


@router.get("/agents")
def list_agents() -> dict[str, Any]:
    from app.main import get_llm_router, _run_coro_sync

    runtime = get_llm_router()
    _run_coro_sync(runtime.discover_agents(force=False))
    return {"ok": True, "count": len(runtime.list_agents()), "agents": runtime.list_agents()}


@router.post("/agents/{name}/reload")
def reload_agent(name: str) -> dict[str, Any]:
    from app.main import get_llm_router, _run_coro_sync

    runtime = get_llm_router()
    result = _run_coro_sync(runtime.reload_single_agent(name))
    if not bool(result.get("ok")):
        raise HTTPException(status_code=404, detail=str(result.get("error") or "reload failed"))
    return result

