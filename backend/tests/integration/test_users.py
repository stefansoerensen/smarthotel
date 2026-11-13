"""User management by admins, own password for everyone."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import auth_headers, create_tenant


async def _login(client: AsyncClient, username: str, password: str) -> int:
    response = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    return response.status_code


async def test_admin_creates_lists_and_changes_users(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    tenant = await create_tenant(db, code="GRPU")
    created = await client.post(
        "/api/users",
        json={
            "username": "rezeption",
            "password": "Start12345!",
            "role": "operator",
            "tenant_code": "GRPU",
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    assert created.json() == {
        "username": "rezeption",
        "role": "operator",
        "tenant_code": "GRPU",
        "is_active": True,
    }
    assert await _login(client, "rezeption", "Start12345!") == 200

    listed = await client.get("/api/users", headers=admin_headers)
    assert "rezeption" in {u["username"] for u in listed.json()["items"]}

    reset = await client.patch(
        "/api/users/rezeption", json={"password": "Neu12345678!"}, headers=admin_headers
    )
    assert reset.status_code == 200
    assert await _login(client, "rezeption", "Neu12345678!") == 200

    off = await client.patch(
        "/api/users/rezeption", json={"is_active": False}, headers=admin_headers
    )
    assert off.json()["is_active"] is False
    assert await _login(client, "rezeption", "Neu12345678!") == 401
    assert tenant.code == "GRPU"


async def test_rules_for_new_users(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    no_tenant = await client.post(
        "/api/users",
        json={"username": "op1", "password": "Start12345!", "role": "operator"},
        headers=admin_headers,
    )
    assert no_tenant.status_code == 422
    assert no_tenant.json()["code"] == "user.tenant_required"
    short = await client.post(
        "/api/users",
        json={"username": "op2", "password": "kurz", "role": "admin"},
        headers=admin_headers,
    )
    assert short.status_code == 422
    await client.post(
        "/api/users",
        json={"username": "dup", "password": "Start12345!", "role": "admin"},
        headers=admin_headers,
    )
    again = await client.post(
        "/api/users",
        json={"username": "dup", "password": "Start12345!", "role": "admin"},
        headers=admin_headers,
    )
    assert again.status_code == 409


async def test_last_active_admin_cannot_be_deactivated(
    client: AsyncClient, db: AsyncSession
) -> None:
    from sqlalchemy import update

    from app.models.platform.user import User

    await db.execute(update(User).values(is_active=False))
    headers = await auth_headers(db, role="admin")
    me = (await client.get("/api/auth/me", headers=headers)).json()["username"]
    response = await client.patch(f"/api/users/{me}", json={"is_active": False}, headers=headers)
    assert response.status_code == 422
    assert response.json()["code"] == "user.last_admin"


async def test_operator_sees_own_tenant_users_only(client: AsyncClient, db: AsyncSession) -> None:
    own = await create_tenant(db)
    other = await create_tenant(db)
    mine = await auth_headers(db, role="operator", tenant=own)
    await auth_headers(db, role="operator", tenant=other)
    listed = await client.get("/api/users", headers=mine)
    assert listed.status_code == 200
    assert {u["tenant_code"] for u in listed.json()["items"]} == {own.code}
    forbidden = await client.post(
        "/api/users",
        json={
            "username": "x1",
            "password": "Start12345!",
            "role": "operator",
            "tenant_code": own.code,
        },
        headers=mine,
    )
    assert forbidden.status_code == 403


async def test_change_own_password(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    await client.post(
        "/api/users",
        json={"username": "selbst", "password": "Start12345!", "role": "admin"},
        headers=admin_headers,
    )
    token = (
        await client.post("/api/auth/login", json={"username": "selbst", "password": "Start12345!"})
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    wrong = await client.post(
        "/api/auth/password",
        json={"old_password": "falsch", "new_password": "Anders12345!"},
        headers=headers,
    )
    assert wrong.status_code == 401
    ok = await client.post(
        "/api/auth/password",
        json={"old_password": "Start12345!", "new_password": "Anders12345!"},
        headers=headers,
    )
    assert ok.status_code == 204
    assert await _login(client, "selbst", "Anders12345!") == 200


async def test_deactivated_user_token_stops_working(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await client.post(
        "/api/users",
        json={"username": "weg", "password": "Start12345!", "role": "admin"},
        headers=admin_headers,
    )
    token = (
        await client.post("/api/auth/login", json={"username": "weg", "password": "Start12345!"})
    ).json()["access_token"]
    await client.patch("/api/users/weg", json={"is_active": False}, headers=admin_headers)
    assert (
        await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 401
