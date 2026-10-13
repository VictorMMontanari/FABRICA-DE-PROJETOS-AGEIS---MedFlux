"""Validadores reutilizados pelos schemas Pydantic."""

import re

SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"
_SPACES = re.compile(r"\s+")


def normalize_email(value: str) -> str:
    return value.strip().lower()


def clean_name(value: str) -> str:
    name = _SPACES.sub(" ", value).strip()
    if len(name) < 2:
        raise ValueError("Nome deve ter ao menos 2 caracteres.")
    if not any(ch.isalpha() for ch in name):
        raise ValueError("Nome deve conter letras.")
    return name


def validate_password(value: str) -> str:
    if len(value) < 6:
        raise ValueError("A senha deve ter no mínimo 6 caracteres.")
    # Limite do bcrypt: bytes além de 72 seriam ignorados silenciosamente.
    if len(value.encode("utf-8")) > 72:
        raise ValueError("A senha deve ter no máximo 72 bytes.")
    if not value.strip():
        raise ValueError("A senha não pode ser composta apenas por espaços.")
    return value


def clean_text(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("O texto não pode estar vazio.")
    return text
