import httpx
import pytest

from tests.conftest import FakeFileRepository, auth_headers, register

pytestmark = pytest.mark.anyio

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64


async def test_get_and_update_profile(client: httpx.AsyncClient) -> None:
    session = await register(client)
    headers = auth_headers(session)

    response = await client.put(
        "/api/v1/users/me",
        json={"name": "  Marina   Souza Santos ", "email": "Marina@Novo.com", "city": "Bauru, SP"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Marina Souza Santos"
    assert body["email"] == "marina@novo.com"
    assert body["city"] == "Bauru, SP"
    assert body["avatarInitials"] == "MS"

    me = await client.get("/api/v1/users/me", headers=headers)
    assert me.json()["email"] == "marina@novo.com"


async def test_update_profile_email_conflict_and_empty_body(client: httpx.AsyncClient) -> None:
    await register(client, email="outra@medflux.com", name="Outra Pessoa")
    session = await register(client)

    conflict = await client.put("/api/v1/users/me", json={"email": "outra@medflux.com"}, headers=auth_headers(session))
    assert conflict.status_code == 409
    empty = await client.put("/api/v1/users/me", json={}, headers=auth_headers(session))
    assert empty.status_code == 422


async def test_upload_avatar_to_minio(client: httpx.AsyncClient, fake_files: FakeFileRepository) -> None:
    session = await register(client)
    headers = auth_headers(session)
    user_id = session["user"]["id"]

    response = await client.post(
        "/api/v1/users/me/avatar", files={"file": ("foto.png", PNG_BYTES, "image/png")}, headers=headers
    )
    assert response.status_code == 200, response.text
    upload = response.json()
    assert upload["bucket"] == "medflux-users"
    assert upload["object_name"].startswith(f"{user_id}/avatar-")
    assert upload["object_name"].endswith(".png")
    assert upload["content_type"] == "image/png"
    assert upload["size"] == len(PNG_BYTES)
    assert upload["url"].startswith("http://minio.test/medflux-users/")
    assert fake_files.objects[("medflux-users", upload["object_name"])].data == PNG_BYTES

    profile = (await client.get("/api/v1/users/me", headers=headers)).json()
    assert profile["avatar_url"] and upload["object_name"] in profile["avatar_url"]

    # Nova foto substitui a anterior no MinIO.
    second = await client.post(
        "/api/v1/users/me/avatar", files={"file": ("foto.jpg", JPEG_BYTES, "image/jpeg")}, headers=headers
    )
    assert second.status_code == 200
    assert ("medflux-users", upload["object_name"]) not in fake_files.objects
    assert len(fake_files.objects) == 1


async def test_upload_avatar_rejects_invalid_files(client: httpx.AsyncClient) -> None:
    headers = auth_headers(await register(client))

    fake_image = await client.post(
        "/api/v1/users/me/avatar", files={"file": ("x.png", b"<script>alert(1)</script>", "image/png")}, headers=headers
    )
    assert fake_image.status_code == 415

    too_big = PNG_BYTES + b"\x00" * (5 * 1024 * 1024)
    big = await client.post("/api/v1/users/me/avatar", files={"file": ("big.png", too_big, "image/png")}, headers=headers)
    assert big.status_code == 413

    unauthenticated = await client.post("/api/v1/users/me/avatar", files={"file": ("x.png", PNG_BYTES, "image/png")})
    assert unauthenticated.status_code == 401


async def test_files_endpoint_only_serves_own_files(client: httpx.AsyncClient) -> None:
    owner = await register(client)
    other = await register(client, email="outra@medflux.com", name="Outra Pessoa")
    upload = (
        await client.post(
            "/api/v1/users/me/avatar", files={"file": ("f.png", PNG_BYTES, "image/png")}, headers=auth_headers(owner)
        )
    ).json()
    path = f"/api/v1/files/medflux-users/{upload['object_name']}"

    own = await client.get(path, headers=auth_headers(owner))
    assert own.status_code == 200
    assert own.content == PNG_BYTES
    assert own.headers["content-type"] == "image/png"

    assert (await client.get(path, headers=auth_headers(other))).status_code == 404
    assert (await client.get("/api/v1/files/outro-bucket/x.png", headers=auth_headers(owner))).status_code == 404
    traversal = await client.get(f"/api/v1/files/medflux-users/{owner['user']['id']}/../x", headers=auth_headers(owner))
    assert traversal.status_code == 404
