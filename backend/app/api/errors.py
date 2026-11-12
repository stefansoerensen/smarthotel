"""Translate application exceptions into HTTP responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.core.errors import AppError

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Install exception handlers on ``app``."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> Response:
        logger.info("AppError %s on %s: %s", exc.code, request.url.path, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code, "details": exc.details},
        )
