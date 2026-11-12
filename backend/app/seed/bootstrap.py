"""Bootstrap data for every start: the administrator, dev users outside production.

Run as the pre-deploy command (``python -m app.seed.bootstrap``) after ``alembic upgrade head``.
It must stay idempotent and must never abort a release over missing optional configuration.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.seed.users import ensure_dev_users
from app.services.platform import users

logger = logging.getLogger(__name__)


async def ensure_admin_user(session: AsyncSession) -> None:
    """Create the administrator named by ``ADMIN_USERNAME``/``ADMIN_PASSWORD`` when it is absent.

    Never resets an existing account's password: a running deployment must not lose its admin
    because a variable changed. Without a password no account is created at all — that is a
    warning, not a failure, because this runs as the pre-deploy command and must not block a
    release.
    """
    username = settings.admin_username.strip()
    password = settings.admin_password
    if not username or not password:
        logger.warning("ADMIN_USERNAME/ADMIN_PASSWORD not configured; no administrator was created")
        return
    if await users.get_user_by_username(session, username) is not None:
        return
    await users.create_user(session, username=username, password=password, role="admin")
    logger.info("created administrator %s", username)


async def bootstrap(session: AsyncSession) -> None:
    """Insert the configured administrator and, outside production, dev users."""
    await ensure_admin_user(session)
    if settings.environment != "production":
        await ensure_dev_users(session)


async def _main() -> None:
    """Open a session, bootstrap it and commit."""
    async with SessionLocal() as session:
        await bootstrap(session)
        await session.commit()
    logger.info("bootstrap complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
