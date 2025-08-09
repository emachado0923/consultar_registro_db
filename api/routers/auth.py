from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from api.core.database import engine_analitica
from api.core.security import (
    create_token,
    decode_token,
    hash_password_with_salt,
    verify_password,
)
from api.models.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterUserRequest,
    TokenResponse,
)

router = APIRouter()
auth_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_scheme)) -> Dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta token Bearer")
    token = credentials.credentials
    data = decode_token(token)
    return data


def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user.get("username") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
    return user


@router.post("/login", response_model=TokenResponse, tags=["Auth"])
def login(body: LoginRequest):
    q = text(
        """
        SELECT username, password_hash, sal, activo, nombre_completo
        FROM usuarios
        WHERE username = :username
        """
    )
    with engine_analitica.connect() as conn:
        row = conn.execute(q, {"username": body.username}).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña inválidos")

    stored_hash = row[1]
    salt = row[2]
    active = bool(row[3])
    full_name = row[4]

    if not active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta desactivada")
    if not (stored_hash and salt) or not verify_password(salt, stored_hash, body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña inválidos")

    token = create_token({"username": body.username, "full_name": full_name})
    return TokenResponse(access_token=token, user={"username": body.username, "full_name": full_name})


@router.post("/change-password", tags=["Auth"])
def change_password(body: ChangePasswordRequest, user: Dict[str, Any] = Depends(get_current_user)):
    username = user["username"]

    with engine_analitica.connect() as conn:
        row = conn.execute(text("SELECT password_hash, sal FROM usuarios WHERE username=:u"), {"u": username}).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        stored_hash, salt = row[0], row[1]
        if not verify_password(salt, stored_hash, body.current_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta")

        new_vals = hash_password_with_salt(body.new_password)
        conn.execute(
            text("UPDATE usuarios SET password_hash=:h, sal=:s WHERE username=:u"),
            {"h": new_vals["hash"], "s": new_vals["salt"], "u": username},
        )
        conn.commit()
    return {"status": "ok"}


@router.post("/register", tags=["Auth"])
def register_user(body: RegisterUserRequest, _: Dict[str, Any] = Depends(require_admin)):
    with engine_analitica.connect() as conn:
        exists = conn.execute(text("SELECT COUNT(*) FROM usuarios WHERE username=:u"), {"u": body.username}).scalar()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario ya existe")

        vals = hash_password_with_salt(body.password)
        conn.execute(
            text(
                """
                INSERT INTO usuarios (username, password_hash, sal, nombre_completo, activo)
                VALUES (:u, :h, :s, :n, 1)
                """
            ),
            {"u": body.username, "h": vals["hash"], "s": vals["salt"], "n": body.full_name},
        )
        conn.commit()
    return {"status": "ok"}
