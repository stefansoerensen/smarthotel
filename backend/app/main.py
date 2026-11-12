"""FastAPI application factory."""

import logging
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.edge.v1 import router as edge_router
from app.api.errors import register_error_handlers
from app.api.native import api_router
from app.core.config import settings
from app.core.ratelimit import RateLimiter

logger = logging.getLogger(__name__)

_API_PREFIXES = ("api", "edge")


def mount_static(app: FastAPI) -> None:
    """Serve the built frontend from ``settings.static_dir`` with a single-page-app fallback.

    Called last, so the ``/api`` router matches first. An unmatched path under ``/api`` gets a
    JSON 404 — a mistyped API path must never answer with HTML. Without a build nothing is
    mounted and the API is unaffected.
    """
    static_dir = Path(settings.static_dir).resolve()
    index_file = static_dir / "index.html"

    for prefix in _API_PREFIXES:

        @app.api_route(
            f"/{prefix}/{{path:path}}",
            methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
            include_in_schema=False,
            name=f"{prefix}_not_found",
        )
        async def api_not_found(path: str) -> Response:
            """Unknown API path: JSON 404."""
            return JSONResponse({"detail": "Not Found"}, status_code=404)

    if not index_file.is_file():
        logger.warning("no %s; the frontend is not served by this process", index_file)
        return

    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def spa(path: str) -> Response:
        """Return a built file when one exists, else ``index.html`` for client-side routing."""
        if path.split("/", 1)[0] in _API_PREFIXES:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        if path:
            candidate = (static_dir / path).resolve()
            if candidate.is_file() and candidate.is_relative_to(static_dir):
                return FileResponse(candidate)
        return FileResponse(index_file, headers={"Cache-Control": "no-cache"})

    logger.info("serving the frontend from %s", static_dir)


def create_app() -> FastAPI:
    """Build the FastAPI application with middleware, routers and handlers."""
    app = FastAPI(title="Smart Building", version="0.1.0")
    app.state.login_limiter = RateLimiter(max_calls=10, period_seconds=60)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    @app.get("/api/health", tags=["health"])
    async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
        """Liveness plus database connectivity check."""
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}

    app.include_router(api_router)
    app.include_router(edge_router)
    mount_static(app)
    return app


app = create_app()
