"""Contrato comum dos agentes de saúde."""

from dataclasses import dataclass, field
from typing import Any, ClassVar

from app.agents.runtime import AgentRuntime
from app.services.ai_service import parse_json_object
from app.services.prompt_service import PromptService


@dataclass
class AgentContext:
    """Tudo que os agentes sabem sobre a interação atual."""

    user_id: str
    user_name: str
    session_id: str
    message: str
    history: list[dict[str, str]] = field(default_factory=list)
    diseases: list[dict[str, Any]] = field(default_factory=list)
    past_queries: list[str] = field(default_factory=list)

    @property
    def first_name(self) -> str:
        return self.user_name.split()[0] if self.user_name.split() else "paciente"

    @property
    def patient_text(self) -> str:
        """Todas as falas do paciente na sessão + a atual: sintomas citados antes continuam valendo."""
        previous = [item["content"] for item in self.history if item["role"] == "user"]
        return "\n".join([*previous, self.message])


class BaseAgent:
    name: ClassVar[str]

    def __init__(self, runtime: AgentRuntime, prompts: PromptService) -> None:
        self.runtime = runtime
        self.prompts = prompts

    async def ask_text(self, system_prompt: str, user_prompt: str) -> str | None:
        return await self.runtime.complete(self.name, system_prompt, user_prompt)

    async def ask_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        text = await self.runtime.complete(self.name, system_prompt, user_prompt, json_mode=True)
        return parse_json_object(text) if text else None
