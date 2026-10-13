from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Formato único de erro da API."""

    code: str = Field(examples=["invalid_credentials"])
    message: str = Field(examples=["Email ou senha inválidos."])
    details: Any = None


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """Documenta no Swagger os erros possíveis de um endpoint."""
    descriptions = {
        400: "Requisição inválida",
        401: "Não autenticado, token inválido ou credenciais erradas",
        403: "Sem permissão",
        404: "Não encontrado",
        409: "Conflito (ex.: email já cadastrado)",
        413: "Arquivo grande demais",
        415: "Tipo de arquivo não suportado",
        422: "Erro de validação dos campos",
        429: "Muitas tentativas",
        503: "Serviço externo indisponível",
    }
    return {code: {"model": ErrorResponse, "description": descriptions[code]} for code in codes}
