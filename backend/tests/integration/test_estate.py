"""Tenants (Mandanten) and properties (Häuser)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import auth_headers, create_property, create_tenant, events_of


async def test_admin_creates_tenant_and_property(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    tenant = await client.post(
        "/api/tenants", json={"code": "GRP", "name": "Hotelgruppe Nord"}, headers=admin_headers
    )
    assert tenant.status_code == 201, tenant.text

    prop = await client.post(
        "/api/properties",
        json={"tenant_code": "GRP", "code": "HAM1", "name": "Neubau Hamburg", "city": "Hamburg"},
        headers=admin_headers,
    )
    assert prop.status_code == 201, prop.text
    body = prop.json()
    assert body["code"] == "HAM1"
    assert body["tenant_code"] == "GRP"
    assert body["time_zone"] == "Europe/Berlin"
    assert await events_of(db, "property", "HAM1") == ["created"]
    assert await events_of(db, "tenant", "GRP") == ["created"]


async def test_codes_are_unique(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    await client.post("/api/tenants", json={"code": "DUP", "name": "A"}, headers=admin_headers)
    again = await client.post(
        "/api/tenants", json={"code": "DUP", "name": "B"}, headers=admin_headers
    )
    assert again.status_code == 409
    assert again.json()["code"] == "tenant.code_taken"


async def test_patch_property_records_a_change(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    prop = await create_property(db, code="PAT1")
    response = await client.patch(
        f"/api/properties/{prop.code}", json={"name": "Neuer Name"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Neuer Name"
    assert await events_of(db, "property", "PAT1") == ["created", "changed"]


async def test_operator_sees_only_own_tenant(client: AsyncClient, db: AsyncSession) -> None:
    own = await create_tenant(db)
    other = await create_tenant(db)
    mine = await create_property(db, tenant=own)
    theirs = await create_property(db, tenant=other)
    headers = await auth_headers(db, role="operator", tenant=own)

    listed = await client.get("/api/properties", headers=headers)
    codes = {item["code"] for item in listed.json()["items"]}
    assert mine.code in codes
    assert theirs.code not in codes

    assert (await client.get(f"/api/properties/{theirs.code}", headers=headers)).status_code == 404
    assert (await client.get(f"/api/properties/{mine.code}", headers=headers)).status_code == 200


async def test_operator_cannot_create_tenants_or_properties(
    client: AsyncClient, db: AsyncSession
) -> None:
    own = await create_tenant(db)
    headers = await auth_headers(db, role="operator", tenant=own)
    response = await client.post("/api/tenants", json={"code": "X", "name": "X"}, headers=headers)
    assert response.status_code == 403
    response = await client.post(
        "/api/properties",
        json={"tenant_code": own.code, "code": "NOPE", "name": "x"},
        headers=headers,
    )
    assert response.status_code == 403


async def test_unknown_time_zone_is_rejected(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    tenant = await create_tenant(db)
    response = await client.post(
        "/api/properties",
        json={"tenant_code": tenant.code, "code": "TZ1", "name": "x", "time_zone": "Mars/Base"},
        headers=admin_headers,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "property.invalid_time_zone"


async def test_admin_renames_a_tenant(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    tenant = await create_tenant(db, code="REN")
    response = await client.patch(
        f"/api/tenants/{tenant.code}", json={"name": "Neuer Name"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Neuer Name"
    assert response.json()["code"] == "REN"
    assert await events_of(db, "tenant", "REN") == ["created", "changed"]


async def test_operator_cannot_rename_a_tenant(client: AsyncClient, db: AsyncSession) -> None:
    own = await create_tenant(db)
    headers = await auth_headers(db, role="operator", tenant=own)
    response = await client.patch(f"/api/tenants/{own.code}", json={"name": "X"}, headers=headers)
    assert response.status_code == 403
