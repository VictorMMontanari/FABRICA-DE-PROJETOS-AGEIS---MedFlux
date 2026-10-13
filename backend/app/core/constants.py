"""Constantes de domínio compartilhadas entre camadas."""

from datetime import timedelta, timezone
from enum import StrEnum

# Brasil não tem horário de verão desde 2019: offset fixo evita depender de tzdata.
BRT = timezone(timedelta(hours=-3), "BRT")

EMERGENCY_PHONE = "192"


class UnitType(StrEnum):
    UPA = "UPA"
    UBS = "UBS"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class TriageStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CLOSED = "closed"


class Severity(StrEnum):
    EMERGENCY = "emergencia"
    URGENT = "urgente"
    MODERATE = "moderada"
    MILD = "leve"
    UNKNOWN = "indefinida"


class Bucket(StrEnum):
    USERS = "medflux-users"
    TRIAGE = "medflux-triage"
    DOCUMENTS = "medflux-documents"


class VectorCollection(StrEnum):
    DISEASES = "diseases"
    SYMPTOMS = "symptoms"
    AGENT_HISTORY = "agent_history"
    USER_QUERIES = "user_queries"
    MEDICAL_CONTEXT = "medical_context"


# Coleções com dados de um usuário: toda busca é filtrada por user_id.
USER_SCOPED_COLLECTIONS = frozenset({VectorCollection.AGENT_HISTORY, VectorCollection.USER_QUERIES})

AVATAR_MAX_BYTES = 5 * 1024 * 1024

TRIAGE_STATUS_LABELS = {
    TriageStatus.ACTIVE: "Em andamento",
    TriageStatus.COMPLETED: "Triagem concluída",
    TriageStatus.CLOSED: "Encerrada",
}

# Termos normalizados (minúsculos, sem acento). Usados pelo fallback determinístico e
# como rede de segurança: um sinal de alarme detectado aqui nunca é rebaixado pelo LLM.
EMERGENCY_TERMS: tuple[str, ...] = (
    "dor no peito",
    "aperto no peito",
    "falta de ar",
    "dificuldade para respirar",
    "nao consigo respirar",
    "desmaio",
    "desmaiei",
    "desmaiou",
    "convulsao",
    "convulsionando",
    "perda de consciencia",
    "boca torta",
    "fraqueza de um lado",
    "dormencia de um lado",
    "fala enrolada",
    "sangramento intenso",
    "vomitando sangue",
    "labios roxos",
    "pensamento suicida",
    "quero me matar",
)

URGENT_TERMS: tuple[str, ...] = (
    "febre alta",
    "febre muito alta",
    "febre persistente",
    "vomito",
    "vomitando",
    "vomitei",
    "dor forte",
    "dor intensa",
    "insuportavel",
    "sangue",
    "sangrando",
    "desidratacao",
    "rigidez na nuca",
    "manchas vermelhas",
    "queimadura",
    "fratura",
    "machucado profundo",
)

# Sintoma canônico -> variantes normalizadas encontradas no texto livre.
SYMPTOM_LEXICON: dict[str, tuple[str, ...]] = {
    "febre": ("febre", "febril", "temperatura alta"),
    "tosse": ("tosse", "tossindo"),
    "dor de cabeça": ("dor de cabeca", "cefaleia", "enxaqueca"),
    "dor abdominal": ("dor abdominal", "dor na barriga", "dor de barriga", "dor no estomago", "colica"),
    "dor no peito": ("dor no peito", "aperto no peito"),
    "falta de ar": ("falta de ar", "dificuldade para respirar", "nao consigo respirar", "cansaco para respirar"),
    "náusea": ("nausea", "enjoo", "enjoado", "enjoada"),
    "vômito": ("vomito", "vomitando", "vomitei"),
    "diarreia": ("diarreia", "intestino solto"),
    "dor de garganta": ("dor de garganta", "garganta inflamada"),
    "coriza": ("coriza", "nariz escorrendo", "nariz entupido", "congestao nasal"),
    "dor no corpo": ("dor no corpo", "corpo dolorido", "mialgia"),
    "tontura": ("tontura", "tonto", "tonta", "vertigem"),
    "desmaio": ("desmaio", "desmaiei", "desmaiou", "perda de consciencia"),
    "manchas na pele": ("manchas", "manchas vermelhas", "erupcao", "coceira na pele"),
    "dor ao urinar": ("dor ao urinar", "ardencia ao urinar", "ardor ao urinar", "xixi ardendo"),
    "cansaço": ("cansaco", "fadiga", "fraqueza"),
    "dor nas costas": ("dor nas costas", "dor lombar"),
    "sangramento": ("sangramento", "sangrando", "sangue"),
    "pressão alta": ("pressao alta", "hipertensao"),
}
