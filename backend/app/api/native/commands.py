"""Commands sent to gateways, for the operator's view."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_scoped_property
from app.models.estate.property import Property
from app.schemas.native.common import Page
from app.services.edge import commands

router = APIRouter(tags=["edge"])


class CommandOut(BaseModel):
    """A command and its state."""

    id: uuid.UUID
    device_code: str
    point_key: str
    value: float
    status: str
    created_at: datetime
    sent_at: datetime | None
    acked_at: datetime | None
    detail: str | None


@router.get("/properties/{property_code}/commands", response_model=Page[CommandOut])
async def list_commands(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    prop: Property = Depends(get_scoped_property),
    db: AsyncSession = Depends(get_db),
) -> Page[CommandOut]:
    """Commands of a property, newest first."""
    rows, total = await commands.list_for_property(db, prop, skip=skip, limit=limit)
    return Page(
        items=[
            CommandOut(
                id=c.id,
                device_code=c.device_code,
                point_key=c.point_key,
                value=c.value,
                status=c.status,
                created_at=c.created_at,
                sent_at=c.sent_at,
                acked_at=c.acked_at,
                detail=c.detail,
            )
            for c in rows
        ],
        total=total,
    )
