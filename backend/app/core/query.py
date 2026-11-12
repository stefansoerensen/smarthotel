"""Generic query helpers shared by services."""

import uuid
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError


async def paginate(
    session: AsyncSession, stmt: Select[Any], *, skip: int, limit: int
) -> tuple[list[Any], int]:
    """Execute ``stmt`` with offset/limit and return (rows, total count)."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    rows = (await session.execute(stmt.offset(skip).limit(limit))).scalars().all()
    return list(rows), int(total)


async def get_by_key(
    session: AsyncSession,
    model: Any,
    key: uuid.UUID | str,
    entity: str,
    *,
    code_attr: str = "code",
    for_update: bool = False,
) -> Any:
    """Load ``model`` by UUID id or by business code; raise NotFoundError if missing."""
    column = model.id if isinstance(key, uuid.UUID) else getattr(model, code_attr)
    stmt = select(model).where(column == key)
    if for_update:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise NotFoundError(entity, key)
    return obj
