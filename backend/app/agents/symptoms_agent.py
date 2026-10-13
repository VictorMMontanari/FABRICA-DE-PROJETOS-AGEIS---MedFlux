"""Agente de sintomas: extrai sintomas e sinais de alarme e estima a gravidade."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.agents.base_agent import AgentContext, BaseAgent
from app.core.constants import EMERGENCY_TERMS, SYMPTOM_LEXICON, URGENT_TERMS, Severity
from app.core.logging import get_logger
from app.utils.embeddings import normalize_text

logger = get_logger(__name__)

SEVERITY_RANK = {
    Severity.UNKNOWN: 0,
    Severity.MILD: 1,
    Severity.MODERATE: 2,
    Severity.URGENT: 3,
    Severity.EMERGENCY: 4,
}


@dataclass
class SymptomAnalysis:
    symptoms: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    severity: Severity = Severity.UNKNOWN
    source: Literal["llm", "fallback"] = "fallback"


class _LLMSymptoms(BaseModel):
    symptoms: list[str] = []
    red_flags: list[str] = []
    severity: Severity = Severity.UNKNOWN


def _contains(text: str, term: str) -> bool:
    """Casa no início de palavra: "vomito" também encontra "vomitos"."""
    return f" {term}" in f" {text}"


def analyze_with_rules(text: str) -> SymptomAnalysis:
    """Análise determinística por palavras-chave (texto normalizado, sem acentos).

    ponytail: não trata negação ("não tenho dor no peito" conta como sinal de alarme). O viés é
    intencionalmente conservador (excesso de UPA, nunca falta); para refinar, adicionar detecção de negação.
    """
    normalized = normalize_text(text)
    symptoms = [name for name, variants in SYMPTOM_LEXICON.items() if any(_contains(normalized, v) for v in variants)]
    emergency = [term for term in EMERGENCY_TERMS if _contains(normalized, term)]
    urgent = [term for term in URGENT_TERMS if _contains(normalized, term)]

    if emergency:
        severity = Severity.EMERGENCY
    elif urgent:
        severity = Severity.URGENT
    elif symptoms:
        severity = Severity.MILD
    else:
        severity = Severity.UNKNOWN
    return SymptomAnalysis(symptoms=symptoms, red_flags=emergency + urgent, severity=severity)


def _merge_unique(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for item in (value.strip() for group in groups for value in group):
        key = normalize_text(item)
        if item and key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


class SymptomsAgent(BaseAgent):
    name = "symptoms_agent"

    async def run(self, ctx: AgentContext) -> SymptomAnalysis:
        rules = analyze_with_rules(ctx.patient_text)

        system_prompt, user_prompt = self.prompts.symptoms(ctx.message, ctx.history)
        data = await self.ask_json(system_prompt, user_prompt)
        if data is None:
            return rules
        try:
            llm = _LLMSymptoms.model_validate(data)
        except ValidationError:
            logger.warning("symptoms_agent_invalid_llm_output")
            return rules

        # Rede de segurança: o LLM pode elevar a gravidade, nunca rebaixar o que as regras detectaram.
        severity = max(rules.severity, llm.severity, key=SEVERITY_RANK.__getitem__)
        return SymptomAnalysis(
            symptoms=_merge_unique(llm.symptoms, rules.symptoms),
            red_flags=_merge_unique(llm.red_flags, rules.red_flags),
            severity=severity,
            source="llm",
        )
