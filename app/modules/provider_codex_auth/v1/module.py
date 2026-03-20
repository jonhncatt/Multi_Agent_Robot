from __future__ import annotations

from typing import Any

from app.codex_runner import CodexResponsesRunner


class CodexAuthProviderModule:
    module_id = "provider_codex_auth"
    version = "1.0.0"
    auth_mode = "codex_auth"

    def build_runner(
        self,
        *,
        agent: Any,
        auth: Any,
        model: str,
        max_output_tokens: int,
        use_responses_api: bool | None = None,
    ) -> Any:
        return CodexResponsesRunner(
            auth_manager=agent._auth_manager,
            model=model,
            max_output_tokens=max_output_tokens,
            temperature=agent.config.openai_temperature,
            ai_message_cls=agent._AIMessage,
        )
