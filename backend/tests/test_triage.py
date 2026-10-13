import uuid

import httpx
import pytest

from tests.conftest import FakeFileRepository, auth_headers, register

pytestmark = pytest.mark.anyio


async def send(client: httpx.AsyncClient, headers: dict[str, str], session_id: str, message: str) -> httpx.Response:
    return await client.post("/api/v1/triage/message", json={"session_id": session_id, "message": message}, headers=headers)


async def test_create_triage_session(client: httpx.AsyncClient) -> None:
    headers = auth_headers(await register(client))

    response = await client.post("/api/v1/triage/session", json={"title": "Dor nas costas"}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Dor nas costas"
    assert body["status"] == "active"
    assert body["summary"] is None
    uuid.UUID(body["id"])

    custom_id = str(uuid.uuid4())
    created = await client.post("/api/v1/triage/session", json={"session_id": custom_id}, headers=headers)
    assert created.status_code == 201 and created.json()["id"] == custom_id
    duplicate = await client.post("/api/v1/triage/session", json={"session_id": custom_id}, headers=headers)
    assert duplicate.status_code == 409


async def test_triage_response_with_fallback_when_openrouter_is_off(
    client: httpx.AsyncClient, openrouter_calls: list[object], fake_files: FakeFileRepository
) -> None:
    session = await register(client)
    headers = auth_headers(session)
    session_id = str(uuid.uuid4())  # id gerado pelo frontend, sessão ainda não existe

    response = await send(client, headers, session_id, "Estou com dor no peito e falta de ar desde cedo")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "fallback"
    assert body["session_id"] == session_id
    assert len(body["timestamp"]) == 5 and body["timestamp"][2] == ":"
    recommendation = body["triage_recommendation"]
    assert set(recommendation) == {"required", "unit_type", "urgency_label", "title", "description", "warning"}
    assert recommendation["required"] is True
    assert recommendation["unit_type"] == "UPA"
    assert recommendation["urgency_label"] == "UPA - Atendimento Imediato"
    assert "192" in recommendation["warning"] or "192" in recommendation["title"]
    assert openrouter_calls == []  # sem API key nenhuma chamada externa

    # Transcrição da triagem concluída arquivada no bucket medflux-triage.
    assert ("medflux-triage", f"{session['user']['id']}/{session_id}.json") in fake_files.objects


async def test_fallback_routes_mild_symptoms_to_ubs_and_asks_details_on_greeting(client: httpx.AsyncClient) -> None:
    headers = auth_headers(await register(client))

    greeting = (await send(client, headers, str(uuid.uuid4()), "Oi, tudo bem?")).json()
    assert greeting["triage_recommendation"] is None
    assert "sentindo" in greeting["reply"]

    mild = (await send(client, headers, str(uuid.uuid4()), "Estou com tosse e coriza há dois dias")).json()
    assert mild["triage_recommendation"]["unit_type"] == "UBS"
    assert mild["triage_recommendation"]["urgency_label"] == "UBS - Atendimento Básico"

    urgent = (await send(client, headers, str(uuid.uuid4()), "Tenho febre alta e estou vomitando")).json()
    assert urgent["triage_recommendation"]["urgency_label"] == "UPA - Atendimento Hoje"


async def test_symptoms_from_previous_messages_are_kept(client: httpx.AsyncClient) -> None:
    headers = auth_headers(await register(client))
    session_id = str(uuid.uuid4())

    await send(client, headers, session_id, "Oi")
    await send(client, headers, session_id, "Estou com dor no peito")
    follow_up = (await send(client, headers, session_id, "Começou faz uma hora")).json()
    assert follow_up["triage_recommendation"]["unit_type"] == "UPA"


async def test_history_and_session_detail_persist_chat(client: httpx.AsyncClient) -> None:
    headers = auth_headers(await register(client))
    session_id = str(uuid.uuid4())
    await send(client, headers, session_id, "Estou com dor de barriga e enjoo")

    history = await client.get("/api/v1/triage/history", headers=headers)
    assert history.status_code == 200
    items = history.json()
    assert len(items) == 1
    item = items[0]
    assert {"id", "title", "description", "timestamp", "status", "route"} <= set(item)
    assert item["id"] == session_id
    assert item["title"] == "Dor abdominal"
    assert item["status"] == "Encaminhado para UBS"
    assert item["route"] == "/chat"
    assert item["timestamp"].startswith("Hoje, ")
    assert item["description"].startswith("Orientação para UBS • Hoje, ")
    assert item["summary"].startswith("Sintomas relatados:")

    detail = await client.get(f"/api/v1/triage/session/{session_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "completed"
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]
    assert body["messages"][0]["content"] == "Estou com dor de barriga e enjoo"
    assert body["messages"][1]["triage_recommendation"]["unit_type"] == "UBS"


async def test_sessions_are_private_per_user(client: httpx.AsyncClient) -> None:
    owner = auth_headers(await register(client))
    intruder = auth_headers(await register(client, email="outra@medflux.com", name="Outra Pessoa"))
    session_id = str(uuid.uuid4())
    await send(client, owner, session_id, "Dor de cabeça")

    assert (await client.get(f"/api/v1/triage/session/{session_id}", headers=intruder)).status_code == 404
    assert (await send(client, intruder, session_id, "invadindo")).status_code == 404
    assert (await client.get("/api/v1/triage/history", headers=intruder)).json() == []
    assert (await client.get("/api/v1/triage/history")).status_code == 401


async def test_triage_message_validation(client: httpx.AsyncClient) -> None:
    headers = auth_headers(await register(client))
    assert (await send(client, headers, "curto", "febre")).status_code == 422
    assert (await send(client, headers, str(uuid.uuid4()), "   ")).status_code == 422


async def test_health_units_for_map(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health/units")
    assert response.status_code == 200
    units = response.json()
    assert len(units) == 2
    upa = next(unit for unit in units if unit["type"] == "UPA")
    assert upa["position"] == [upa["latitude"], upa["longitude"]]
    assert set(upa) == {"id", "name", "type", "address", "latitude", "longitude", "position"}

    only_ubs = (await client.get("/api/v1/health/units", params={"type": "UBS"})).json()
    assert [unit["type"] for unit in only_ubs] == ["UBS"]
