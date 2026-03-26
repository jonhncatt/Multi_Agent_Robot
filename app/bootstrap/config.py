from __future__ import annotations

from dataclasses import dataclass

from app.config import AppConfig


@dataclass(slots=True)
class AgentOSAssembleConfig:
    kernel_version: str = "1.0.0"
    include_research_module: bool = True
    include_coding_module: bool = True
    include_adaptation_module: bool = True
    enable_session_provider: bool = True


def build_assemble_config(app_config: AppConfig) -> AgentOSAssembleConfig:
    return AgentOSAssembleConfig(
        kernel_version="1.0.0",
        include_research_module=True,
        include_coding_module=True,
        include_adaptation_module=True,
        enable_session_provider=bool(app_config.enable_session_tools),
    )
