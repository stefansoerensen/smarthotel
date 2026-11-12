"""Development users; created only outside production."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.platform import users

DEV_USERS: list[tuple[str, str, str]] = [
    ("admin", "Admin123!", "admin"),
]


async def ensure_dev_users(session: AsyncSession) -> None:
    """Create the development users if they do not exist."""
    for username, password, role in DEV_USERS:
        if await users.get_user_by_username(session, username) is None:
            await users.create_user(session, username=username, password=password, role=role)
