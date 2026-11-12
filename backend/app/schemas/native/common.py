"""Shared schema pieces."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """A list response: ``{"items": [...], "total": n}``."""

    items: list[T]
    total: int
