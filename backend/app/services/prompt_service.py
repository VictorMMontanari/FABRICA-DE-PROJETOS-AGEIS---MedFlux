"""Monta os prompts dos agentes a partir dos templates em app/prompts."""

from collections.abc import Sequence
from typing import Any

from app.core.constants import MessageRole
from app.prompts.assistant_prompt import SUMMARIZER_SYSTEM, build_summarizer_user_prompt
from app.prompts.disease_lookup_prompt import SYMPTOMS_SYSTEM, build_symptoms_user_prompt, format_disease_context
from app.prompts.triage_prompt import TRIAGE_SYSTEM, build_triage_user_prompt

MAX_HISTORY_CHARS = 3000


def format_history(history: Sequence[dict[str, str]]) -> str:
    """Conversa em texto, mantendo as mensagens mais recentes dentro do limite de caracteres."""
    lines: list[str] = []
    total = 0
    for item in reversed(history):
        speaker = "Paciente" if item["role"] == MessageRole.USER else "Clara"
        line = f"{speaker}: {item['content']}"
        total += len(line)
        if total > MAX_HISTORY_CHARS:
            break
        lines.append(line)
    return "\n".join(reversed(lines))


class PromptService:
    def symptoms(self, message: str, history: Sequence[dict[str, str]]) -> tuple[str, str]:
        return SYMPTOMS_SYSTEM, build_symptoms_user_prompt(message, format_history(history))

    def triage(
        self,
        *,
        patient_name: str,
        message: str,
        history: Sequence[dict[str, str]],
        symptoms: list[str],
        red_flags: list[str],
        severity: str,
        diseases: list[dict[str, Any]],
        past_queries: list[str],
    ) -> tuple[str, str]:
        return TRIAGE_SYSTEM, build_triage_user_prompt(
            patient_name=patient_name,
            message=message,
            history=format_history(history),
            symptoms=symptoms,
            red_flags=red_flags,
            severity=severity,
            clinical_context=format_disease_context(diseases),
            past_queries=past_queries,
        )

    def summary(self, history: Sequence[dict[str, str]], recommendation: str) -> tuple[str, str]:
        return SUMMARIZER_SYSTEM, build_summarizer_user_prompt(format_history(history), recommendation)
