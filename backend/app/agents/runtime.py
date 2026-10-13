"""Runtimes de agentes: a camada que de fato executa o LLM para um agente.

Os agentes (triage/symptoms/summarizer) só conhecem `AgentRuntime.complete`. Trocar a implementação
(AGENT_RUNTIME=custom|ag2) não altera agentes, serviços nem endpoints.
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.ai_service import AIService

if TYPE_CHECKING:
    from ag2.config import ModelConfig

logger = get_logger(__name__)


class AgentRuntime(ABC):
    name: str

    @property
    @abstractmethod
    def available(self) -> bool:
        """False quando não há LLM configurado: os agentes vão direto para o fallback."""

    @abstractmethod
    async def complete(
        self, agent_name: str, system_prompt: str, user_prompt: str, *, json_mode: bool = False
    ) -> str | None:
        """Texto gerado pelo LLM, ou None em qualquer falha (o agente aplica o fallback determinístico)."""


class CustomRuntime(AgentRuntime):
    """Chama o OpenRouter diretamente pelo cliente HTTP próprio."""

    name = "custom"

    def __init__(self, ai: AIService) -> None:
        self.ai = ai

    @property
    def available(self) -> bool:
        return self.ai.available

    async def complete(
        self, agent_name: str, system_prompt: str, user_prompt: str, *, json_mode: bool = False
    ) -> str | None:
        return await self.ai.complete(system_prompt, user_prompt, json_mode=json_mode)


class AG2Runtime(AgentRuntime):
    """Executa cada agente como um `ag2.Agent` (framework AG2, sucessor do AutoGen) via OpenRouter."""

    name = "ag2"

    def __init__(self, settings: Settings, config_factory: Callable[[bool], "ModelConfig"] | None = None) -> None:
        from ag2 import Agent  # import tardio: AG2 só é carregado quando este runtime é escolhido

        self._agent_cls = Agent
        self._settings = settings
        self._config_factory = config_factory or self._openrouter_config
        self._has_custom_config = config_factory is not None

    @property
    def available(self) -> bool:
        return self._settings.openrouter_enabled or self._has_custom_config

    def _openrouter_config(self, json_mode: bool) -> "ModelConfig":
        from ag2.config import OpenAIConfig

        extra_body: dict[str, Any] | None = {"response_format": {"type": "json_object"}} if json_mode else None
        return OpenAIConfig(
            model=self._settings.OPENROUTER_MODEL,
            api_key=self._settings.OPENROUTER_API_KEY,
            base_url=self._settings.OPENROUTER_BASE_URL,
            temperature=0.2,
            max_tokens=800,
            timeout=self._settings.OPENROUTER_TIMEOUT,
            max_retries=1,
            default_headers={"X-Title": self._settings.APP_NAME},
            extra_body=extra_body,
        )

    async def complete(
        self, agent_name: str, system_prompt: str, user_prompt: str, *, json_mode: bool = False
    ) -> str | None:
        if not self.available:
            return None
        try:
            agent = self._agent_cls(agent_name, prompt=system_prompt, config=self._config_factory(json_mode))
            reply = await asyncio.wait_for(agent.ask(user_prompt), timeout=self._settings.OPENROUTER_TIMEOUT + 5)
            return reply.body
        except Exception as exc:  # noqa: BLE001 - qualquer falha do framework cai no fallback
            logger.warning("ag2_fallback", extra={"agent": agent_name, "error": type(exc).__name__})
            return None


def build_runtime(settings: Settings, ai: AIService) -> AgentRuntime:
    if settings.AGENT_RUNTIME == "ag2":
        try:
            return AG2Runtime(settings)
        except ImportError:
            logger.warning("ag2_not_installed_using_custom_runtime")
    return CustomRuntime(ai)
