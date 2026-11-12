"""Login and current-user schemas."""

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    """Credentials."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """A Bearer token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    """The authenticated user."""

    model_config = ConfigDict(from_attributes=True)

    username: str
    role: str
    tenant_code: str | None = None
