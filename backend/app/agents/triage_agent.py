"""Agente de triagem: decide UPA x UBS e redige a orientação ao paciente."""

from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError

from app.agents.base_agent import AgentContext, BaseAgent
from app.agents.symptoms_agent import SymptomAnalysis
from app.core.constants import EMERGENCY_PHONE, Severity, UnitType
from app.core.logging import get_logger
from app.schemas.triage import TriageRecommendation
from app.utils.embeddings import normalize_text

logger = get_logger(__name__)

_MENTAL_HEALTH_TERMS = ("suicid", "me matar", "tirar minha vida")
_UPA_REQUIRED = (Severity.EMERGENCY, Severity.URGENT)


@dataclass
class TriageDecision:
    reply: str
    recommendation: TriageRecommendation | None
    source: Literal["llm", "fallback"]


def fallback_decision(ctx: AgentContext, analysis: SymptomAnalysis) -> TriageDecision:
    """Resposta determinística com a mesma estrutura do LLM, usada quando a IA está indisponível."""
    name = ctx.first_name
    symptoms = ", ".join(analysis.symptoms[:4])

    if analysis.severity == Severity.UNKNOWN:
        return TriageDecision(
            reply=(
                f"Oi, {name}! Para eu te orientar com segurança, me conte o que você está sentindo, "
                "há quanto tempo e se a intensidade é leve, moderada ou forte."
            ),
            recommendation=None,
            source="fallback",
        )

    if analysis.severity == Severity.EMERGENCY:
        flags = ", ".join(analysis.red_flags[:3]) or "sinais de gravidade"
        warning = f"Não vá dirigindo sozinho(a). Se houver piora ou perda de consciência, ligue {EMERGENCY_PHONE}."
        if any(term in normalize_text(ctx.patient_text) for term in _MENTAL_HEALTH_TERMS):
            warning = f"Você não está sozinho(a): ligue {EMERGENCY_PHONE} ou para o CVV no 188 (24h, gratuito)."
        recommendation = TriageRecommendation(
            required=True,
            unit_type=UnitType.UPA.value,
            urgency_label="UPA - Atendimento Imediato",
            title=f"Procure atendimento de emergência agora ou ligue {EMERGENCY_PHONE}",
            description=f"Você relatou {flags}, o que pode indicar uma situação grave que precisa de avaliação imediata.",
            warning=warning,
        )
        reply = f"{name}, o que você descreveu exige atenção imediata. Ligue {EMERGENCY_PHONE} ou vá agora à UPA."
    elif analysis.severity == Severity.URGENT:
        recommendation = TriageRecommendation(
            required=True,
            unit_type=UnitType.UPA.value,
            urgency_label="UPA - Atendimento Hoje",
            title="Procure uma UPA ainda hoje",
            description=(
                "Os sintomas indicam necessidade de avaliação presencial para descartar condições "
                "que exigem cuidado imediato."
            ),
            warning=f"Se a dor ficar insuportável, houver desmaio ou vômito contínuo, ligue {EMERGENCY_PHONE}.",
        )
        reply = f"Entendi, {name}. Pelos sinais que você contou, o ideal é ser avaliado(a) presencialmente hoje."
    else:
        recommendation = TriageRecommendation(
            required=True,
            unit_type=UnitType.UBS.value,
            urgency_label="UBS - Atendimento Básico",
            title="Procure uma UBS nas próximas horas",
            description=(
                "O quadro descrito parece estável, mas merece acompanhamento clínico para orientar "
                "o cuidado inicial com segurança."
            ),
            warning="Se houver piora súbita, febre alta persistente ou dor intensa, procure atendimento de urgência.",
        )
        reply = f"Obrigada por explicar, {name}. Organizei a orientação mais adequada para o seu caso."

    if symptoms:
        reply += f" Sintomas considerados: {symptoms}."
    return TriageDecision(reply=reply, recommendation=recommendation, source="fallback")


class TriageAgent(BaseAgent):
    name = "triage_agent"

    async def run(self, ctx: AgentContext, analysis: SymptomAnalysis) -> TriageDecision:
        system_prompt, user_prompt = self.prompts.triage(
            patient_name=ctx.user_name,
            message=ctx.message,
            history=ctx.history,
            symptoms=analysis.symptoms,
            red_flags=analysis.red_flags,
            severity=analysis.severity.value,
            diseases=ctx.diseases,
            past_queries=ctx.past_queries,
        )
        data = await self.ask_json(system_prompt, user_prompt)
        if data is None:
            return fallback_decision(ctx, analysis)

        reply = data.get("reply")
        raw_recommendation = data.get("triage_recommendation")
        try:
            recommendation = TriageRecommendation.model_validate(raw_recommendation) if raw_recommendation else None
        except ValidationError:
            logger.warning("triage_agent_invalid_llm_output")
            return fallback_decision(ctx, analysis)
        if not isinstance(reply, str) or not reply.strip():
            return fallback_decision(ctx, analysis)

        # Segurança do paciente: sinais de urgência/emergência sempre resultam em UPA.
        if analysis.severity in _UPA_REQUIRED and (recommendation is None or recommendation.unit_type != "UPA"):
            logger.warning("triage_agent_safety_override", extra={"severity": analysis.severity.value})
            return fallback_decision(ctx, analysis)
        # Com sintomas descritos, a triagem precisa terminar com uma orientação.
        if recommendation is None and analysis.severity != Severity.UNKNOWN:
            return fallback_decision(ctx, analysis)

        return TriageDecision(reply=reply.strip(), recommendation=recommendation, source="llm")
