"""Login and the current user."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.platform import users


async def test_login_returns_a_token_that_identifies_the_user(
    client: AsyncClient, db: AsyncSession
) -> None:
    await users.create_user(db, username="anna", password="Secret123!", role="operator")
    response = await client.post(
        "/api/auth/login", json={"username": "anna", "password": "Secret123!"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "anna"
    assert me.json()["role"] == "operator"
    assert "password_hash" not in me.json()


async def test_wrong_password_is_401(client: AsyncClient, db: AsyncSession) -> None:
    await users.create_user(db, username="ben", password="Secret123!", role="operator")
    response = await client.post("/api/auth/login", json={"username": "ben", "password": "nope"})
    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_credentials"


async def test_me_without_token_is_401(client: AsyncClient) -> None:
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_login_is_rate_limited(client: AsyncClient) -> None:
    codes = [
        (await client.post("/api/auth/login", json={"username": "x", "password": "y"})).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429
