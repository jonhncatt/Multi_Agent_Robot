from __future__ import annotations

from packages.runtime_core.capability_loader import MemoryModule


def build_office_memory_modules() -> tuple[MemoryModule, ...]:
    return (
        MemoryModule(
            module_id="overlay_memory",
            title="Overlay Memory Module",
            description="记录长期对话信号、个体偏好和模块亲和度。",
            default=True,
            signal_kinds=("intent_counts", "domain_terms", "module_affinity", "response_style"),
            metadata={"family": "office", "store": "EvolutionStore"},
        ),
    )
