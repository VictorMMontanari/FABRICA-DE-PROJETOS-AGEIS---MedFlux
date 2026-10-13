"""Agente de resumo: gera o texto curto salvo em TriageSession.summary."""

from app.agents.base_agent import AgentContext, BaseAgent
from app.agents.symptoms_agent import SymptomAnalysis
from app.agents.triage_agent import TriageDecision

MAX_SUMMARY_CHARS = 280


def fallback_summary(analysis: SymptomAnalysis, decision: TriageDecision) -> str:
    symptoms = ", ".join(analysis.symptoms[:5]) or "não especificados"
    label = decision.recommendation.urgency_label if decision.recommendation else "sem orientação"
    return f"Sintomas relatados: {symptoms}. Orientação: {label}."[:MAX_SUMMARY_CHARS]


class SummarizerAgent(BaseAgent):
    name = "summarizer_agent"

    async def run(self, ctx: AgentContext, analysis: SymptomAnalysis, decision: TriageDecision) -> str:
        if decision.recommendation is None:
            return fallback_summary(analysis, decision)

        conversation = [*ctx.history, {"role": "user", "content": ctx.message}]
        system_prompt, user_prompt = self.prompts.summary(conversation, decision.recommendation.urgency_label)
        text = await self.ask_text(system_prompt, user_prompt)
        if not text or not text.strip():
            return fallback_summary(analysis, decision)
        summary = " ".join(text.split())
        return summary if len(summary) <= MAX_SUMMARY_CHARS else summary[: MAX_SUMMARY_CHARS - 1].rstrip() + "…"
