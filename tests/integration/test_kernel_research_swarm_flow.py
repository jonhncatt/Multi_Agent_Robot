from __future__ import annotations

from app.bootstrap import AgentOSAssembleConfig, assemble_runtime
from app.config import load_config
from app.contracts import HealthReport, TaskRequest, ToolCall, ToolResult
from tests.support_agent_os import bind_fake_research_provider


class FailingSwarmProvider:
    provider_id = "failing_swarm_provider"
    supported_tools = ["web.search", "web.fetch"]

    def execute(self, call: ToolCall) -> ToolResult:
        return ToolResult(
            ok=False,
            tool_name=call.name,
            provider_id=self.provider_id,
            error=f"simulated swarm provider failure for {call.name}",
        )

    def health_check(self) -> HealthReport:
        return HealthReport(component_id=self.provider_id, status="healthy", summary="failing swarm provider ready")


def test_kernel_dispatch_research_swarm_request_handles_serial_replay_and_join_trace() -> None:
    runtime = assemble_runtime(
        load_config(),
        assemble_config=AgentOSAssembleConfig(
            include_research_module=True,
            include_coding_module=False,
            include_adaptation_module=False,
            enable_session_provider=True,
        ),
    )
    bind_fake_research_provider(runtime, fail_once_queries={"branch failure note"}, fallback_providers=[])

    response = runtime.dispatch(
        TaskRequest(
            task_id="research-swarm-1",
            task_type="task.research",
            message="run research swarm",
            context={
                "session_id": "research-swarm-session",
                "execution_policy": "research_swarm_pipeline",
                "runtime_profile": "research_swarm_demo",
                "swarm_mode": "parallel_research",
                "swarm_inputs": [
                    {"label": "Architecture brief", "query": "conflict alpha", "input_ref": "brief:architecture"},
                    {"label": "Runtime brief", "query": "conflict beta", "input_ref": "brief:runtime"},
                    {"label": "Failure brief", "query": "branch failure note", "input_ref": "brief:degradation"},
                ],
            },
        ),
        module_id="research_module",
    )

    assert response.ok is True
    swarm = dict(response.payload.get("swarm") or {})
    business = dict(swarm.get("business_output") or {})
    assert response.payload["result_grade"] == "insufficient_evidence"
    assert response.payload["return_strategy"] == "report_swarm_unreliable_and_offer_refine_or_escalate"
    assert swarm["branch_count"] == 3
    assert swarm["degradation"]["degraded"] is True
    assert swarm["result_grade"] == "insufficient_evidence"
    assert swarm["return_strategy"] == "report_swarm_unreliable_and_offer_refine_or_escalate"
    assert len(swarm["aggregation"]["conflicts"]) >= 1
    assert any(item["attempt_mode"] == "serial_replay" for item in swarm["branches"])
    assert business["overall_summary"]["branch_count"] == 3
    assert business["per_branch_evidence"][2]["branch_status"] == "degraded"
    assert business["per_branch_evidence"][2]["included_in_final_merge"] is True
    assert business["conflict_and_degradation_notes"]["conflict_detected"] is True
    assert "Shared Research Conflict" in business["conflict_and_degradation_notes"]["conflict_summary"]
    assert "serial_replay triggered" in business["conflict_and_degradation_notes"]["degradation_reason"]
    assert "Reliability note:" in response.text

    trace = runtime.kernel.health_snapshot()["recent_traces"][-1]
    assert trace["module_id"] == "research_module"
    assert trace["execution_policy"] == "research_swarm_pipeline"
    assert trace["runtime_profile"] == "research_swarm_demo"
    assert trace["selected_roles"] == ["researcher", "aggregator"]
    assert trace["selected_tools"] == ["web.search", "web.fetch"]
    assert trace["selected_providers"] == ["fake_research_provider"]
    stages = [event["stage"] for event in trace["events"]]
    assert "swarm_branch_plan" in stages
    assert "swarm_branch_result" in stages
    assert "swarm_degradation" in stages
    assert "swarm_join" in stages


def test_kernel_dispatch_research_swarm_request_returns_degraded_when_replay_recovers_cleanly() -> None:
    runtime = assemble_runtime(
        load_config(),
        assemble_config=AgentOSAssembleConfig(
            include_research_module=True,
            include_coding_module=False,
            include_adaptation_module=False,
            enable_session_provider=True,
        ),
    )
    bind_fake_research_provider(
        runtime,
        fail_once_queries={"branch recovery note"},
        fallback_providers=[],
        results_by_query={
            "unique alpha": [
                {
                    "title": "Alpha Finding",
                    "url": "https://example.com/alpha-finding",
                    "snippet": "Alpha branch evidence.",
                    "domain": "example.com",
                    "score": 9.2,
                    "source": "fake_research",
                },
                {
                    "title": "Alpha Support",
                    "url": "https://example.com/alpha-support",
                    "snippet": "Alpha branch support.",
                    "domain": "example.com",
                    "score": 8.6,
                    "source": "fake_research",
                },
            ],
            "unique beta": [
                {
                    "title": "Beta Finding",
                    "url": "https://example.com/beta-finding",
                    "snippet": "Beta branch evidence.",
                    "domain": "example.com",
                    "score": 9.1,
                    "source": "fake_research",
                },
                {
                    "title": "Beta Support",
                    "url": "https://example.com/beta-support",
                    "snippet": "Beta branch support.",
                    "domain": "example.com",
                    "score": 8.4,
                    "source": "fake_research",
                },
            ],
            "branch recovery note": [
                {
                    "title": "Recovery Finding",
                    "url": "https://example.com/recovery-finding",
                    "snippet": "Recovered branch evidence.",
                    "domain": "example.com",
                    "score": 8.8,
                    "source": "fake_research",
                },
                {
                    "title": "Recovery Support",
                    "url": "https://example.com/recovery-support",
                    "snippet": "Recovered branch support.",
                    "domain": "example.com",
                    "score": 8.1,
                    "source": "fake_research",
                },
            ],
        },
    )

    response = runtime.dispatch(
        TaskRequest(
            task_id="research-swarm-degraded-clean",
            task_type="task.research",
            message="run research swarm degraded clean",
            context={
                "session_id": "research-swarm-degraded-clean",
                "execution_policy": "research_swarm_pipeline",
                "runtime_profile": "research_swarm_demo",
                "swarm_mode": "parallel_research",
                "swarm_inputs": [
                    {"label": "Alpha brief", "query": "unique alpha", "input_ref": "brief:alpha"},
                    {"label": "Beta brief", "query": "unique beta", "input_ref": "brief:beta"},
                    {"label": "Recovery brief", "query": "branch recovery note", "input_ref": "brief:recovery"},
                ],
            },
        ),
        module_id="research_module",
    )

    assert response.ok is True
    assert response.payload["result_grade"] == "degraded"
    assert response.payload["return_strategy"] == "return_swarm_summary_with_caveat"
    assert response.payload["swarm"]["business_output"]["conflict_and_degradation_notes"]["conflict_detected"] is False
    assert response.payload["swarm"]["business_output"]["per_branch_evidence"][2]["branch_status"] == "degraded"


def test_kernel_dispatch_research_swarm_request_returns_failed_when_all_branches_fail() -> None:
    runtime = assemble_runtime(
        load_config(),
        assemble_config=AgentOSAssembleConfig(
            include_research_module=True,
            include_coding_module=False,
            include_adaptation_module=False,
            enable_session_provider=True,
        ),
    )
    runtime.kernel.register_provider(FailingSwarmProvider())
    for tool_name in ("web.search", "web.fetch"):
        contract = runtime.kernel.registry.get_tool_contract(tool_name)
        assert contract is not None
        runtime.kernel.registry.register_tool_contract(
            contract,
            primary_provider="failing_swarm_provider",
            fallback_providers=[],
        )

    response = runtime.dispatch(
        TaskRequest(
            task_id="research-swarm-hard-fail",
            task_type="task.research",
            message="run failing research swarm",
            context={
                "session_id": "research-swarm-hard-fail",
                "execution_policy": "research_swarm_pipeline",
                "runtime_profile": "research_swarm_demo",
                "swarm_mode": "parallel_research",
                "swarm_inputs": [
                    {"label": "Alpha brief", "query": "alpha fail", "input_ref": "brief:alpha"},
                    {"label": "Beta brief", "query": "beta fail", "input_ref": "brief:beta"},
                ],
            },
        ),
        module_id="research_module",
    )

    assert response.ok is False
    assert response.payload["result_grade"] == "failed"
    assert response.payload["return_strategy"] == "report_swarm_failure"
    assert response.payload["swarm"]["failed_branch_count"] == 2
