"""Cliente HTTP assíncrono para a API do OpenRouter (compatível com OpenAI Chat Completions)."""

from typing import Any

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenRouterError(Exception):
    """Falha de rede, timeout, status HTTP de erro ou resposta fora do formato esperado."""


class OpenRouterClient:
    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self._http = http
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return self._settings.openrouter_enabled

    @property
    def model(self) -> str:
        return self._settings.OPENROUTER_MODEL

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> str:
        if not self.enabled:
            raise OpenRouterError("OPENROUTER_API_KEY não configurada.")

        body: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self._settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": self._settings.cors_origins[0] if self._settings.cors_origins else "http://localhost",
            "X-Title": self._settings.APP_NAME,
        }
        url = f"{self._settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"

        try:
            response = await self._http.post(url, json=body, headers=headers, timeout=self._settings.OPENROUTER_TIMEOUT)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            logger.warning("openrouter_http_error", extra={"status": exc.response.status_code})
            raise OpenRouterError(f"OpenRouter respondeu {exc.response.status_code}") from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            logger.warning("openrouter_request_failed", extra={"error": type(exc).__name__})
            raise OpenRouterError(str(exc) or type(exc).__name__) from exc

        if not isinstance(content, str) or not content.strip():
            raise OpenRouterError("Resposta vazia do modelo.")
        return content
