"""Exception types raised by services and translated by API error handlers."""

from typing import Any


class AppError(Exception):
    """Base application error with a stable machine-readable code."""

    status_code: int = 400

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details: dict[str, Any] = details or {}


class DomainError(AppError):
    """A business rule was violated."""

    status_code = 422


class NotFoundError(AppError):
    """A referenced entity does not exist."""

    status_code = 404

    def __init__(self, entity: str, key: object) -> None:
        super().__init__(
            f"{entity}.not_found",
            f"{entity} '{key}' not found",
            {"entity": entity, "key": str(key)},
        )


class ConflictError(AppError):
    """The request conflicts with existing state (e.g. duplicate code)."""

    status_code = 409


class AuthError(AppError):
    """Authentication failed."""

    status_code = 401
