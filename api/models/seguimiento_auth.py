from typing import Any, Dict

from pydantic import BaseModel, Field


class LoginSeguimientoRequest(BaseModel):
    usuario: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenSeguimientoResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: Dict[str, Any]
    primer_login: bool = False


class CambiarPasswordPrimerLoginRequest(BaseModel):
    """
    Cambio de contraseña obligatorio en el primer login (no exige la
    contraseña actual, igual que el flujo de Streamlit — el usuario llega
    aquí porque primer_login=1, ya validado por el login).
    """
    nueva_password: str = Field(min_length=8)
