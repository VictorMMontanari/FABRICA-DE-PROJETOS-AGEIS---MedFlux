from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.utils.validators import clean_name, normalize_email


class UserResponse(BaseModel):
    """Perfil público do usuário. `avatarInitials` em camelCase: contrato do frontend (UserProfile)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    email: EmailStr
    city: str
    avatar_url: str | None = None
    avatar_initials: str = Field(serialization_alias="avatarInitials")
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    city: str | None = Field(default=None, max_length=120)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return clean_name(value) if value is not None else None

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return normalize_email(value) if value is not None else None

    @field_validator("city")
    @classmethod
    def _city(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def _at_least_one(self) -> "UserUpdate":
        if self.name is None and self.email is None and self.city is None:
            raise ValueError("Informe ao menos um campo para atualizar.")
        return self
