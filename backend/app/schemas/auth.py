from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserResponse
from app.utils.validators import clean_name, normalize_email, validate_password


class UserCreate(BaseModel):
    name: str = Field(max_length=120, examples=["Marina Santos"])
    email: EmailStr = Field(examples=["marina.santos@medflux.com"])
    password: str = Field(examples=["123456"])
    city: str = Field(default="", max_length=120, examples=["Marília, SP"])

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_name(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("city")
    @classmethod
    def _city(cls, value: str) -> str:
        return value.strip()


class UserLogin(BaseModel):
    email: EmailStr = Field(examples=["marina.santos@medflux.com"])
    password: str = Field(min_length=1, max_length=128, examples=["123456"])

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return normalize_email(value)


class TokenResponse(BaseModel):
    """`token` + `user` é o formato que o frontend grava na sessão."""

    token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse
