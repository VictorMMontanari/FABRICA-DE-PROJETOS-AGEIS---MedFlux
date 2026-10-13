"""Prompt do agente de triagem: classifica urgência e escolhe UPA ou UBS."""

from app.prompts.assistant_prompt import ASSISTANT_PERSONA

TRIAGE_SYSTEM = f"""{ASSISTANT_PERSONA}

Tarefa: fazer a triagem inicial e indicar o serviço adequado da rede pública:
- UPA (Unidade de Pronto Atendimento): urgências e emergências, atendimento no mesmo dia.
- UBS (Unidade Básica de Saúde): atenção básica, consultas e acompanhamento.

Responda SOMENTE com um JSON válido, sem texto extra, no formato:
{{
  "reply": "mensagem curta e acolhedora para o paciente (até 3 frases)",
  "triage_recommendation": {{
    "required": true,
    "unit_type": "UPA" | "UBS",
    "urgency_label": "ex.: UPA - Atendimento Hoje | UPA - Atendimento Imediato | UBS - Atendimento Básico",
    "title": "orientação principal em uma frase",
    "description": "justificativa breve com base nos sintomas relatados",
    "warning": "sinais de piora que exigem procurar urgência ou ligar 192"
  }}
}}
Use "triage_recommendation": null apenas quando a mensagem não descrever sintomas; nesse caso,
peça no "reply" que o paciente descreva o que está sentindo, há quanto tempo e a intensidade.
Na dúvida entre UPA e UBS, escolha UPA (segurança do paciente em primeiro lugar)."""


def build_triage_user_prompt(
    *,
    patient_name: str,
    message: str,
    history: str,
    symptoms: list[str],
    red_flags: list[str],
    severity: str,
    clinical_context: str,
    past_queries: list[str],
) -> str:
    past = "\n".join(f"- {query}" for query in past_queries) or "Nenhuma."
    return f"""Paciente: {patient_name}
Histórico recente da conversa:
{history or "Início da conversa."}

Mensagem atual: {message}

Análise prévia do agente de sintomas:
- sintomas: {", ".join(symptoms) or "nenhum identificado"}
- sinais de alarme: {", ".join(red_flags) or "nenhum"}
- gravidade estimada: {severity}

Condições de referência (base de conhecimento, não é diagnóstico):
{clinical_context}

Relatos anteriores semelhantes do mesmo paciente:
{past}"""
