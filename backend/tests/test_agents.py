import json
import uuid
from typing import Any

import httpx
import pytest

from app.agents.base_agent import AgentContext
from app.agents.runtime import AG2Runtime, CustomRuntime, build_runtime
from app.agents.symptoms_agent import SymptomsAgent, analyze_with_rules
from app.agents.triage_agent import TriageAgent
from app.core.config import Settings
from app.core.constants import Severity
from app.services.ai_service import AIService, parse_json_object
from app.services.prompt_service import PromptService
from tests.conftest import OpenRouterHandler, auth_headers, chat_completion, register

pytestmark = pytest.mark.anyio

LLM_TRIAGE = {
    "reply": "Marina, pelo que você contou, o ideal é procurar a UBS do seu bairro.",
    "triage_recommendation": {
        "required": True,
        "unit_type": "UBS",
        "urgency_label": "UBS - Atendimento Básico",
        "title": "Agende uma consulta na UBS",
        "description": "Sintomas respiratórios leves, sem sinais de alarme.",
        "warning": "Procure a UPA se surgir falta de ar ou febre alta persistente.",
    },
}


def routed_handler(triage: dict[str, Any] | str, symptoms: dict[str, Any] | None = None) -> OpenRouterHandler:
    """Responde conforme o agente que chamou, identificado pelo prompt de sistema."""

    def handler(body: dict[str, Any]) -> httpx.Response:
        system = body["messages"][0]["content"]
        if "extrair os sintomas" in system:
            return chat_completion(symptoms or {"symptoms": ["tosse"], "red_flags": [], "severity": "leve"})
        if "triagem inicial" in system:
            return chat_completion(triage)
        return chat_completion("Tosse leve há dois dias; orientada a procurar a UBS.")

    return handler


class TestOpenRouterMocked:
    """Integração com o OpenRouter mockado via httpx.MockTransport (sem rede)."""

    @pytest.fixture
    def openrouter_api_key(self) -> str:
        return "sk-or-test"

    @pytest.fixture
    def openrouter_handler(self) -> OpenRouterHandler:
        return routed_handler(LLM_TRIAGE)

    async def test_triage_uses_llm_response(
        self, client: httpx.AsyncClient, openrouter_calls: list[dict[str, Any]]
    ) -> None:
        headers = auth_headers(await register(client))
        session_id = str(uuid.uuid4())
        response = await client.post(
            "/api/v1/triage/message", json={"session_id": session_id, "message": "Estou com tosse"}, headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["source"] == "llm"
        assert body["reply"] == LLM_TRIAGE["reply"]
        assert body["triage_recommendation"] == LLM_TRIAGE["triage_recommendation"]

        assert len(openrouter_calls) == 3  # sintomas, triagem, resumo
        assert all(call["model"] == "openai/gpt-4o-mini" for call in openrouter_calls)
        assert openrouter_calls[0]["response_format"] == {"type": "json_object"}

        detail = (await client.get(f"/api/v1/triage/session/{session_id}", headers=headers)).json()
        assert detail["summary"] == "Tosse leve há dois dias; orientada a procurar a UBS."

        events = (await client.get("/api/v1/agents/history", headers=headers)).json()
        assert {e["agent_name"] for e in events} == {"symptoms_agent", "triage_agent", "summarizer_agent"}
        assert all(e["session_id"] == session_id for e in events)

    async def test_llm_cannot_downgrade_emergency(self, client: httpx.AsyncClient) -> None:
        headers = auth_headers(await register(client))
        response = await client.post(
            "/api/v1/triage/message",
            json={"session_id": str(uuid.uuid4()), "message": "Sinto dor no peito forte"},
            headers=headers,
        )
        body = response.json()
        assert body["triage_recommendation"]["unit_type"] == "UPA"
        assert body["source"] == "fallback"


class TestOpenRouterFailures:
    @pytest.fixture
    def openrouter_api_key(self) -> str:
        return "sk-or-test"

    @pytest.fixture
    def openrouter_handler(self) -> OpenRouterHandler:
        return routed_handler("isto não é json")

    async def test_invalid_llm_output_falls_back(self, client: httpx.AsyncClient) -> None:
        headers = auth_headers(await register(client))
        response = await client.post(
            "/api/v1/triage/message",
            json={"session_id": str(uuid.uuid4()), "message": "Estou com tosse e coriza"},
            headers=headers,
        )
        body = response.json()
        assert body["source"] == "fallback"
        assert body["triage_recommendation"]["unit_type"] == "UBS"


async def test_openrouter_http_error_returns_none(settings: Settings) -> None:
    from app.integrations.openrouter_client import OpenRouterClient

    enabled = settings.model_copy(update={"OPENROUTER_API_KEY": "sk-or-test"})
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(429, json={})))
    ai = AIService(OpenRouterClient(http, enabled))
    assert await ai.complete("sistema", "usuário") is None
    await http.aclose()


def test_parse_json_object_variants() -> None:
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Claro! {"a": 2} Espero ter ajudado') == {"a": 2}
    assert parse_json_object("[1, 2]") is None
    assert parse_json_object("sem json") is None


def test_rules_detect_severity() -> None:
    assert analyze_with_rules("desmaiei hoje cedo").severity == Severity.EMERGENCY
    assert analyze_with_rules("vômitos desde ontem").severity == Severity.URGENT
    assert analyze_with_rules("estou com dor de garganta").severity == Severity.MILD
    assert analyze_with_rules("bom dia").severity == Severity.UNKNOWN


async def test_ag2_runtime_runs_agents(settings: Settings) -> None:
    """Mesmo agente rodando sobre o framework AG2 (LLM roteirizado pelo TestConfig do próprio AG2)."""
    from ag2.testing import TestConfig

    symptoms_json = json.dumps({"symptoms": ["dor de cabeça"], "red_flags": [], "severity": "moderada"})
    runtime = AG2Runtime(settings, config_factory=lambda _json_mode: TestConfig(symptoms_json))
    assert runtime.available

    ctx = AgentContext(user_id="u1", user_name="Marina Santos", session_id="s1", message="Dor de cabeça")
    analysis = await SymptomsAgent(runtime, PromptService()).run(ctx)
    assert analysis.source == "llm"
    assert analysis.severity == Severity.MODERATE
    assert "dor de cabeça" in analysis.symptoms


async def test_runtime_swap_keeps_contract(settings: Settings) -> None:
    from app.integrations.openrouter_client import OpenRouterClient

    ai = AIService(OpenRouterClient(httpx.AsyncClient(), settings))
    assert isinstance(build_runtime(settings, ai), CustomRuntime)
    assert isinstance(build_runtime(settings.model_copy(update={"AGENT_RUNTIME": "ag2"}), ai), AG2Runtime)

    # Runtime sem LLM disponível: TriageAgent cai no fallback determinístico.
    ag2_without_key = AG2Runtime(settings)
    assert not ag2_without_key.available
    ctx = AgentContext(user_id="u1", user_name="Marina", session_id="s1", message="tosse")
    decision = await TriageAgent(ag2_without_key, PromptService()).run(ctx, analyze_with_rules("tosse"))
    assert decision.source == "fallback"
    assert decision.recommendation is not None and decision.recommendation.unit_type == "UBS"


async def test_agent_history_endpoints(client: httpx.AsyncClient) -> None:
    headers = auth_headers(await register(client))
    created = await client.post(
        "/api/v1/agents/history",
        json={"agent_name": "support_agent", "event_type": "note", "input_text": "Paciente pediu retorno", "output": {"ok": True}},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["vector_id"]

    listed = (await client.get("/api/v1/agents/history", headers=headers)).json()
    assert listed[0]["agent_name"] == "support_agent"

    unknown_session = await client.post(
        "/api/v1/agents/history",
        json={"agent_name": "x", "event_type": "y", "session_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert unknown_session.status_code == 404
