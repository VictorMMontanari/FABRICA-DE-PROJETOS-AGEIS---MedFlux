"""Fachada de IA: chama o OpenRouter e devolve None em qualquer falha para que o chamador use o fallback."""

import json
import re
from typing import Any

from app.core.logging import get_logger
from app.integrations.openrouter_client import OpenRouterClient, OpenRouterError

logger = get_logger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_json_object(text: str) -> dict[str, Any] | None:
    """Extrai um objeto JSON de uma resposta de LLM (aceita bloco ```json``` ou texto ao redor)."""
    candidates = [text.strip()]
    if fenced := _JSON_FENCE.search(text):
        candidates.insert(0, fenced.group(1))
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


class AIService:
    def __init__(self, client: OpenRouterClient) -> None:
        self.client = client

    @property
    def available(self) -> bool:
        return self.client.enabled

    async def complete(
        self, system_prompt: str, user_prompt: str, *, json_mode: bool = False, max_tokens: int = 800
    ) -> str | None:
        if not self.available:
            return None
        try:
            return await self.client.chat(
                [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                json_mode=json_mode,
                max_tokens=max_tokens,
            )
        except OpenRouterError as exc:
            logger.warning("ai_fallback", extra={"reason": str(exc)})
            return None

    async def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        text = await self.complete(system_prompt, user_prompt, json_mode=True)
        return parse_json_object(text) if text else None
