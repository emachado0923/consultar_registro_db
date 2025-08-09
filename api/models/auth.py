from typing import Any, Dict
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class RegisterUserRequest(BaseModel):
    username: str = Field(min_length=3)
    full_name: str = Field(min_length=1)
    password: str = Field(min_length=8)
