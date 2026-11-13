"""Importing bus addresses into the registry."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import create_property, events_of


async def _setup(client: AsyncClient, db: AsyncSession, headers: dict[str, str]) -> str:
    code = str((await create_property(db)).code)
    for dev, kind, protocol in [("101-VALVE", "valve", "knx"), ("101-METER", "meter", "modbus")]:
        await client.post(
            f"/api/properties/{code}/devices",
            json={"code": dev, "name": dev, "kind": kind, "protocol": protocol, "location": "101"},
            headers=headers,
        )
    return code


async def test_preview_changes_nothing_and_apply_sets_addresses(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(client, db, admin_headers)
    url = f"/api/properties/{code}/devices/addresses"
    text = "code;address\n101-VALVE;1/2/3\n101-METER;1/40001\nNOPE;1/2/9\n101-VALVE2;x\n"
    preview = await client.post(
        url, content=text, headers={**admin_headers, "Content-Type": "text/plain"}
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["applied"] is False
    assert [(c["device_code"], c["old"], c["new"]) for c in body["changes"]] == [
        ("101-VALVE", None, "1/2/3"),
        ("101-METER", None, "1/40001"),
    ]
    assert [(e["line"], e["message"]) for e in body["errors"]] == [
        (4, "Gerät NOPE gibt es in diesem Haus nicht"),
        (5, "Gerät 101-VALVE2 gibt es in diesem Haus nicht"),
    ]
    device = (
        await client.get(f"/api/properties/{code}/devices/101-VALVE", headers=admin_headers)
    ).json()
    assert device["address"] is None

    applied = await client.post(
        f"{url}?apply=true", content=text, headers={**admin_headers, "Content-Type": "text/plain"}
    )
    assert applied.json()["applied"] is True
    device = (
        await client.get(f"/api/properties/{code}/devices/101-VALVE", headers=admin_headers)
    ).json()
    assert device["address"] == "1/2/3"
    assert await events_of(db, "device", f"{code}/101-VALVE") == ["registered", "changed"]


async def test_knx_addresses_are_checked(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(client, db, admin_headers)
    response = await client.post(
        f"/api/properties/{code}/devices/addresses",
        content="101-VALVE;32/0/0\n",
        headers={**admin_headers, "Content-Type": "text/plain"},
    )
    assert response.json()["changes"] == []
    assert response.json()["errors"][0]["message"] == "Keine gültige KNX-Gruppenadresse: 32/0/0"


async def test_address_set_by_patch_is_checked(
    client: AsyncClient, db: AsyncSession, admin_headers: dict[str, str]
) -> None:
    code = await _setup(client, db, admin_headers)
    url = f"/api/properties/{code}/devices/101-VALVE"
    set_ = await client.patch(url, json={"address": "1/2/5"}, headers=admin_headers)
    assert set_.json()["address"] == "1/2/5"
    bad = await client.patch(url, json={"address": "1/2"}, headers=admin_headers)
    assert bad.status_code == 422
