import httpx
import pytest

from tests.conftest import FakeRedis, auth_headers, register

pytestmark = pytest.mark.anyio


async def test_create_user_returns_session_in_frontend_format(client: httpx.AsyncClient) -> None:
    body = await register(client, email="  Marina.Santos@MedFlux.com ")

    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["token"]
    user = body["user"]
    assert user["name"] == "Marina Santos"
    assert user["email"] == "marina.santos@medflux.com"
    assert user["city"] == "Marília, SP"
    assert user["avatarInitials"] == "MS"
    assert user["avatar_url"] is None
    assert "password" not in str(body) and "password_hash" not in user


async def test_create_user_duplicate_email_conflict(client: httpx.AsyncClient) -> None:
    await register(client)
    response = await client.post(
        "/api/v1/auth/register", json={"name": "Outra", "email": "marina.santos@medflux.com", "password": "abcdef"}
    )
    assert response.status_code == 409
    assert response.json() == {"code": "email_taken", "message": "Email já cadastrado.", "details": None}


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"name": "Ana", "email": "nao-e-email", "password": "123456"}, "email"),
        ({"name": "Ana", "email": "ana@medflux.com", "password": "123"}, "password"),
        ({"name": "1", "email": "ana@medflux.com", "password": "123456"}, "name"),
    ],
)
async def test_create_user_validation(client: httpx.AsyncClient, payload: dict[str, str], field: str) -> None:
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["details"][0]["field"] == field
    assert body["message"].startswith(f"{field}:")


async def test_login_with_correct_password(client: httpx.AsyncClient) -> None:
    await register(client)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "MARINA.SANTOS@medflux.com", "password": "123456"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["avatarInitials"] == "MS"

    me = await client.get("/api/v1/auth/me", headers=auth_headers(body))
    assert me.status_code == 200
    assert me.json()["email"] == "marina.santos@medflux.com"


async def test_login_with_wrong_password(client: httpx.AsyncClient) -> None:
    await register(client)
    response = await client.post("/api/v1/auth/login", json={"email": "marina.santos@medflux.com", "password": "errada"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    assert response.json()["message"] == "Email ou senha inválidos."


async def test_login_unknown_email_has_same_error(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/auth/login", json={"email": "ninguem@medflux.com", "password": "123456"})
    assert response.status_code == 401
    assert response.json()["message"] == "Email ou senha inválidos."


async def test_protected_route_requires_valid_token(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    invalid = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer token-falso"})
    assert invalid.status_code == 401
    assert invalid.json()["code"] == "invalid_token"


async def test_login_rate_limit_with_redis(app: object, client: httpx.AsyncClient) -> None:
    app.state.redis = FakeRedis()  # type: ignore[attr-defined]
    await register(client)
    wrong = {"email": "marina.santos@medflux.com", "password": "errada"}

    for _ in range(5):
        assert (await client.post("/api/v1/auth/login", json=wrong)).status_code == 401
    blocked = await client.post("/api/v1/auth/login", json={**wrong, "password": "123456"})
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limited"


async def test_request_id_and_cors_headers(client: httpx.AsyncClient) -> None:
    response = await client.options(
        "/api/v1/auth/login",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    health = await client.get("/healthz", headers={"X-Request-ID": "abc123"})
    assert health.json() == {"status": "ok"}
    assert health.headers["x-request-id"] == "abc123"


async def test_oauth2_token_endpoint_used_by_swagger(client: httpx.AsyncClient) -> None:
    await register(client)
    ok = await client.post("/api/v1/auth/token", data={"username": "marina.santos@medflux.com", "password": "123456"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["token_type"] == "bearer" and body["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200

    wrong = await client.post("/api/v1/auth/token", data={"username": "marina.santos@medflux.com", "password": "x"})
    assert wrong.status_code == 401
    not_email = await client.post("/api/v1/auth/token", data={"username": "marina", "password": "123456"})
    assert not_email.status_code == 401


async def test_openapi_exposes_password_flow(client: httpx.AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    flow = schema["components"]["securitySchemes"]["JWT"]["flows"]["password"]
    assert flow["tokenUrl"] == "/api/v1/auth/token"
    assert "security" in schema["paths"]["/api/v1/auth/me"]["get"]
    assert (await client.get("/docs")).status_code == 200
