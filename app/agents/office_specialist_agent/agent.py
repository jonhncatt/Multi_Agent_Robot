from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class OfficeSpecialistAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="office_specialist_agent",
            description="办公专家代理，负责文档、汇报、邮件和流程化办公任务。",
            capabilities=["office_workflow", "document_polish", "business_writing"],
            kernel=kernel,
        )

