"""Prompt do agente de sintomas e formatação do contexto clínico recuperado do Qdrant."""

from typing import Any

from app.prompts.assistant_prompt import ASSISTANT_PERSONA

SYMPTOMS_SYSTEM = f"""{ASSISTANT_PERSONA}

Tarefa: extrair os sintomas relatados pelo paciente e classificar a gravidade.
Responda SOMENTE com um JSON válido, sem texto extra, no formato:
{{
  "symptoms": ["sintoma em português", "..."],
  "red_flags": ["sinal de alarme encontrado", "..."],
  "severity": "emergencia" | "urgente" | "moderada" | "leve" | "indefinida"
}}
Critérios de gravidade:
- emergencia: risco imediato à vida (dor no peito, falta de ar intensa, desmaio, convulsão, sinais de AVC,
  sangramento intenso, risco de suicídio).
- urgente: precisa de avaliação presencial no mesmo dia (febre alta persistente, vômitos contínuos, dor intensa,
  desidratação, sangue em fezes/urina/vômito).
- moderada: precisa de consulta, mas pode aguardar algumas horas ou dias.
- leve: sintomas leves que podem ser acompanhados na atenção básica.
- indefinida: a mensagem não descreve sintomas (saudação, dúvida genérica)."""


def build_symptoms_user_prompt(message: str, history: str) -> str:
    history_block = f"Histórico recente da conversa:\n{history}\n\n" if history else ""
    return f"{history_block}Mensagem atual do paciente:\n{message}"


def format_disease_context(diseases: list[dict[str, Any]]) -> str:
    """Transforma resultados de busca vetorial em texto de apoio para o LLM."""
    if not diseases:
        return "Nenhuma condição de referência encontrada."
    lines = []
    for item in diseases:
        symptoms = ", ".join(item.get("symptoms", [])[:8])
        unit = item.get("recommended_unit") or "-"
        lines.append(f"- {item.get('name')}: sintomas típicos {symptoms}. Unidade sugerida: {unit}.")
    return "\n".join(lines)
