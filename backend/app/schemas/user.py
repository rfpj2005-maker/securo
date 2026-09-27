import uuid
from typing import Optional

from fastapi_users import schemas
from pydantic import BaseModel


class UserPreferences(BaseModel):
    language: str = "pt-BR"
    date_format: str = "MM/DD/YYYY"
    timezone: str = "America/Sao_Paulo"
    currency_display: str = "USD"
    onboarding_completed: bool = False
    # Which workspace to land on with no X-Workspace-Id header (a fresh
    # login/device) — see workspace_service.get_default_workspace. Not
    # required to be a valid/current workspace id; an unset or stale value
    # just falls back to "oldest workspace" as before.
    default_workspace_id: Optional[str] = None


class UserRead(schemas.BaseUser[uuid.UUID]):
    preferences: Optional[dict] = None
    is_2fa_enabled: bool = False


class UserCreate(schemas.BaseUserCreate):
    preferences: Optional[dict] = None


class UserUpdate(schemas.BaseUserUpdate):
    preferences: Optional[dict] = None
