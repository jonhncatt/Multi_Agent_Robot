from __future__ import annotations

from typing import Any


class OpenAIAPIProviderModule:
    module_id = "provider_openai_api"
    version = "1.0.0"
    auth_mode = "api_key"

    def build_runner(
        self,
        *,
        agent: Any,
        auth: Any,
        model: str,
        max_output_tokens: int,
        use_responses_api: bool | None = None,
    ) -> Any:
        selected_use_responses = agent.config.openai_use_responses_api if use_responses_api is None else use_responses_api
        kwargs: dict[str, Any] = {
            "model": model,
            "api_key": auth.api_key,
            "max_tokens": max_output_tokens,
            "use_responses_api": selected_use_responses,
        }
        if agent.config.openai_temperature is not None:
            kwargs["temperature"] = agent.config.openai_temperature
        if agent.config.openai_base_url:
            kwargs["base_url"] = agent._normalize_base_url(agent.config.openai_base_url)
        if agent.config.openai_ca_cert_path:
            agent._ensure_openai_ca_env(agent.config.openai_ca_cert_path)
        return agent._ChatOpenAI(**kwargs)
