from __future__ import annotations

import asyncio
import importlib
import json
import os
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI


class LLMRouter:
    """
    极简中央调度器：
    - discover_agents: 扫描 app/agents/*_agent
    - route: 用单一 LLM 产生执行步骤
    - execute: 顺序/并行执行步骤
    - reload_single_agent: 热重载单 Agent
    """

    def __init__(self, kernel: Any) -> None:
        self.kernel = kernel
        self.model = str(os.environ.get("OFFICETOOL_ROUTER_MODEL") or "gpt-4o-mini").strip()
        self.client = self._build_client()
        self.agents: dict[str, Any] = {}
        self.manifests: dict[str, dict[str, Any]] = {}
        self._discover_lock = asyncio.Lock()
        self._reload_lock = asyncio.Lock()

    def _build_client(self) -> AsyncOpenAI | None:
        api_key = (
            str(
                os.environ.get("OPENAI_API_KEY")
                or os.environ.get("OFFICETOOL_LLM_API_KEY")
                or ""
            ).strip()
        )
        if not api_key:
            return None
        base_url = (
            str(
                os.environ.get("OPENAI_BASE_URL")
                or os.environ.get("OFFICETOOL_LLM_BASE_URL")
                or ""
            ).strip()
        )
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        try:
            return AsyncOpenAI(**kwargs)
        except Exception:
            return None

    @property
    def agents_dir(self) -> Path:
        return (Path(__file__).resolve().parent.parent / "agents").resolve()

    def list_agents(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name in sorted(self.manifests.keys()):
            manifest = dict(self.manifests.get(name) or {})
            rows.append(
                {
                    "name": name,
                    "version": str(manifest.get("version") or "1.0"),
                    "description": str(manifest.get("description") or ""),
                    "capabilities": list(manifest.get("capabilities") or []),
                    "loaded": name in self.agents,
                }
            )
        return rows

    def _derive_class_name(self, folder_name: str) -> str:
        base = str(folder_name or "").strip().lower()
        if base.endswith("_agent"):
            base = base[: -len("_agent")]
        camel = "".join(part.capitalize() for part in base.split("_") if part)
        return f"{camel}Agent" if camel else "Agent"

    def _manifest_name_candidates(self, name: str) -> list[str]:
        raw = str(name or "").strip().lower()
        if not raw:
            return []
        candidates = [raw]
        if raw.endswith("_agent"):
            candidates.append(raw[: -len("_agent")])
        else:
            candidates.append(f"{raw}_agent")
        deduped: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            if item and item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped

    async def discover_agents(self, force: bool = False) -> dict[str, Any]:
        async with self._discover_lock:
            if self.agents and not force:
                return {"ok": True, "loaded": sorted(self.agents.keys()), "count": len(self.agents), "cached": True}

            loaded: list[str] = []
            manifests: dict[str, dict[str, Any]] = {}
            agents: dict[str, Any] = {}
            if not self.agents_dir.exists():
                return {"ok": True, "loaded": [], "count": 0, "warning": f"Agents dir not found: {self.agents_dir}"}

            for agent_dir in sorted(self.agents_dir.iterdir(), key=lambda p: p.name):
                if not agent_dir.is_dir():
                    continue
                if not agent_dir.name.endswith("_agent"):
                    continue
                manifest_path = agent_dir / "manifest.json"
                if not manifest_path.exists():
                    continue

                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifest_name = str(manifest.get("name") or agent_dir.name).strip().lower()
                    if not manifest_name:
                        manifest_name = agent_dir.name
                    manifest["name"] = manifest_name
                    module_path = f"app.agents.{agent_dir.name}.agent"
                    mod = importlib.import_module(module_path)
                    class_name = str(manifest.get("entry_class") or "").strip() or self._derive_class_name(agent_dir.name)
                    agent_cls = getattr(mod, class_name)
                    try:
                        instance = agent_cls(kernel=self.kernel)
                    except TypeError:
                        instance = agent_cls()
                    manifests[manifest_name] = manifest
                    agents[manifest_name] = instance
                    loaded.append(manifest_name)
                except Exception as exc:
                    print(f"[LLMRouter] skip broken agent {agent_dir.name}: {exc}")

            self.manifests = manifests
            self.agents = agents
            return {"ok": True, "loaded": sorted(loaded), "count": len(loaded), "cached": False}

    async def reload_single_agent(self, name: str) -> dict[str, Any]:
        async with self._reload_lock:
            await self.discover_agents(force=False)
            candidates = self._manifest_name_candidates(name)
            target = ""
            for item in candidates:
                if item in self.manifests:
                    target = item
                    break
            if not target:
                return {"ok": False, "error": f"Agent not found: {name}"}

            agent_dir = self.agents_dir / target
            if not agent_dir.is_dir():
                return {"ok": False, "error": f"Agent directory not found: {target}"}
            manifest_path = agent_dir / "manifest.json"
            if not manifest_path.exists():
                return {"ok": False, "error": f"Manifest missing: {target}/manifest.json"}

            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest_name = str(manifest.get("name") or target).strip().lower() or target
                module_path = f"app.agents.{agent_dir.name}.agent"
                mod = importlib.import_module(module_path)
                mod = importlib.reload(mod)
                class_name = str(manifest.get("entry_class") or "").strip() or self._derive_class_name(agent_dir.name)
                agent_cls = getattr(mod, class_name)
                try:
                    instance = agent_cls(kernel=self.kernel)
                except TypeError:
                    instance = agent_cls()
                self.manifests[manifest_name] = manifest
                self.agents[manifest_name] = instance
                return {"ok": True, "name": manifest_name, "version": str(manifest.get("version") or "1.0")}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

    async def _json_completion(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 900) -> dict[str, Any]:
        if self.client is None:
            return {"ok": False, "error": "llm client unavailable"}
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raw = str(resp.choices[0].message.content or "").strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.lower().startswith("json"):
                    raw = raw[4:].strip()
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
            return {"ok": False, "error": "Model did not return JSON object"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _fallback_plan(self, user_query: str) -> dict[str, Any]:
        text = str(user_query or "").lower()
        first = "worker_agent"
        if any(key in text for key in ("research", "调研", "资料", "web", "查找", "检索")):
            first = "researcher_agent"
        elif any(key in text for key in ("计划", "规划", "plan", "roadmap", "里程碑")):
            first = "planner_agent"
        elif any(key in text for key in ("代码", "bug", "修复", "refactor", "python", "ts", "js")):
            first = "coder_agent"
        elif any(key in text for key in ("总结", "摘要", "summary")):
            first = "summarizer_agent"

        second = "reviewer_agent"
        if first == "reviewer_agent":
            second = "worker_agent"
        return {
            "plan": "fallback_router",
            "parallel": False,
            "steps": [
                {"agent": first, "task": user_query},
                {"agent": second, "task": "请对上一结果做精炼复核，输出最终可执行答复。"},
            ],
        }

    async def route(self, user_query: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        await self.discover_agents(force=False)
        if not self.agents:
            return {"plan": "fallback_no_agents", "parallel": False, "steps": []}

        agent_lines = []
        for name in sorted(self.manifests.keys()):
            meta = self.manifests.get(name) or {}
            desc = str(meta.get("description") or "")
            capabilities = ", ".join(str(item) for item in list(meta.get("capabilities") or [])[:6])
            agent_lines.append(f"- {name}: {desc}; capabilities={capabilities}")
        agents_info = "\n".join(agent_lines)
        history_hint = ""
        if history:
            recent = [str(item.get("text") or "") for item in history[-3:] if isinstance(item, dict)]
            if recent:
                history_hint = "\n最近上下文：" + " | ".join(recent)

        system_prompt = (
            "你是多 Agent 系统的唯一中央调度器。"
            "目标是最少步骤、最清晰分工。"
            "只返回 JSON，不要解释。"
        )
        user_prompt = (
            f"可用 Agent:\n{agents_info}\n\n"
            f"用户问题：{user_query}{history_hint}\n\n"
            "返回格式必须是：\n"
            "{\n"
            '  "plan": "一句话调度思路",\n'
            '  "parallel": false,\n'
            '  "steps": [\n'
            '    {"agent": "agent_name", "task": "具体任务"}\n'
            "  ]\n"
            "}\n"
            "要求：steps 1~4 步；agent 必须来自可用列表。"
        )
        candidate = await self._json_completion(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.25)
        if not bool(candidate.get("ok", True)) or not isinstance(candidate.get("steps"), list):
            return self._fallback_plan(user_query)

        normalized_steps: list[dict[str, str]] = []
        for raw in list(candidate.get("steps") or []):
            if not isinstance(raw, dict):
                continue
            agent = str(raw.get("agent") or "").strip().lower()
            task = str(raw.get("task") or "").strip()
            if not task:
                continue
            if agent not in self.agents:
                fallback_candidates = self._manifest_name_candidates(agent)
                agent = next((item for item in fallback_candidates if item in self.agents), "")
            if not agent:
                continue
            normalized_steps.append({"agent": agent, "task": task})
            if len(normalized_steps) >= 4:
                break

        if not normalized_steps:
            return self._fallback_plan(user_query)

        return {
            "plan": str(candidate.get("plan") or "llm_router_plan"),
            "parallel": bool(candidate.get("parallel", False)),
            "steps": normalized_steps,
        }

    async def _run_step(self, step: dict[str, Any]) -> dict[str, Any]:
        name = str(step.get("agent") or "").strip().lower()
        task = str(step.get("task") or "").strip()
        if name not in self.agents:
            return {"agent": name, "status": "failed", "error": "Agent not found"}
        agent = self.agents[name]
        try:
            result = await agent.handle_task({"query": task, "context": {"router": "llm_router"}})
            if isinstance(result, dict):
                return {"agent": name, "status": "success", **result}
            return {"agent": name, "status": "success", "result": str(result)}
        except Exception as exc:
            return {"agent": name, "status": "failed", "error": str(exc)}

    async def execute(self, plan: dict[str, Any]) -> dict[str, Any]:
        steps = [item for item in list(plan.get("steps") or []) if isinstance(item, dict)]
        if not steps:
            return {"plan": str(plan.get("plan") or "empty"), "results": []}

        if bool(plan.get("parallel")):
            tasks = [self._run_step(step) for step in steps]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            normalized: list[dict[str, Any]] = []
            for item in results:
                if isinstance(item, Exception):
                    normalized.append({"status": "failed", "error": str(item)})
                else:
                    normalized.append(dict(item))
            return {"plan": str(plan.get("plan") or "parallel"), "results": normalized}

        output: list[dict[str, Any]] = []
        for step in steps:
            output.append(await self._run_step(step))
        return {"plan": str(plan.get("plan") or "sequential"), "results": output}

    async def agent_reason(
        self,
        *,
        agent_name: str,
        agent_description: str,
        capabilities: list[str],
        task: str,
        context: Any | None = None,
    ) -> str:
        if self.client is None:
            return f"{agent_name} fallback: {task}（LLM client unavailable）"
        system_prompt = (
            f"你现在扮演 {agent_name}。\n"
            f"角色说明：{agent_description}\n"
            f"能力：{', '.join(capabilities)}\n"
            "输出要简洁、可执行、避免空话。"
        )
        user_prompt = f"任务：{task}\n上下文：{json.dumps(context or {}, ensure_ascii=False)}"
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=900,
            )
            text = str(resp.choices[0].message.content or "").strip()
            return text or f"{agent_name} 已完成任务。"
        except Exception as exc:
            return f"{agent_name} fallback: {task}（LLM unavailable: {exc}）"

    async def summarize(
        self,
        *,
        user_query: str,
        plan: dict[str, Any],
        execution: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        results = list(execution.get("results") or [])
        if not results:
            return "当前没有可执行结果，请检查 Agent 加载状态。"
        if self.client is None:
            fallback_lines: list[str] = []
            for item in results:
                if not isinstance(item, dict):
                    continue
                agent = str(item.get("agent") or "unknown")
                status = str(item.get("status") or "")
                if status == "success":
                    fallback_lines.append(f"[{agent}] {str(item.get('result') or '')}".strip())
                else:
                    fallback_lines.append(f"[{agent}] failed: {str(item.get('error') or '')}".strip())
            return "\n".join(line for line in fallback_lines if line).strip() or "执行完成。"

        system_prompt = (
            "你是最终答复生成器。基于多 Agent 结果，输出简洁明确的最终答复。"
            "结构：先结论，再关键要点。"
        )
        user_prompt = (
            f"用户问题：{user_query}\n"
            f"调度计划：{json.dumps(plan, ensure_ascii=False)}\n"
            f"执行结果：{json.dumps(results, ensure_ascii=False)}\n"
        )
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.25,
                max_tokens=1200,
            )
            text = str(resp.choices[0].message.content or "").strip()
            if text:
                return text
        except Exception:
            pass

        fallback_lines: list[str] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            agent = str(item.get("agent") or "unknown")
            status = str(item.get("status") or "")
            if status == "success":
                fallback_lines.append(f"[{agent}] {str(item.get('result') or '')}".strip())
            else:
                fallback_lines.append(f"[{agent}] failed: {str(item.get('error') or '')}".strip())
        return "\n".join(line for line in fallback_lines if line).strip() or "执行完成。"
