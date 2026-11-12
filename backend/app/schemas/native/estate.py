"""Tenant and property schemas."""

from pydantic import BaseModel, ConfigDict, Field


class TenantIn(BaseModel):
    """A new tenant."""

    code: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=200)


class TenantOut(BaseModel):
    """A tenant."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    is_active: bool


class PropertyIn(BaseModel):
    """A new property."""

    tenant_code: str
    code: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=200)
    time_zone: str = "Europe/Berlin"
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_code: str = Field(default="DE", min_length=2, max_length=2)


class PropertyPatch(BaseModel):
    """Changes to a property; omitted fields stay as they are."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    time_zone: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_code: str | None = Field(default=None, min_length=2, max_length=2)


class PropertyOut(BaseModel):
    """A property."""

    code: str
    tenant_code: str
    name: str
    time_zone: str
    street: str | None
    postal_code: str | None
    city: str | None
    country_code: str
