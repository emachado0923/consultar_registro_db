from datetime import datetime, timedelta
import hashlib
import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


# =========================
# Configuración y utilidades
# =========================

APP_TITLE = "API de Consulta de Registros - Matrícula Cero 2025-2"

# Cargar variables desde .env (si existe)
load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "24"))


# Valores por defecto ("quemados"). Se pueden sobreescribir por .env/variables de entorno.
DEFAULT_LOGIN_DB = {
    "HOST": "10.124.80.4",
    "USER": "REDACTED",
    "PASSWORD": "REDACTED",
    "DATABASE": "analitica_fondos",
    "PORT": "3306",
}

DEFAULT_APP_DB = {
    "HOST": "10.124.80.4",
    "USER": "REDACTED",
    "PASSWORD": "REDACTED",
    "DATABASE": "REDACTED",
    "PORT": "3306",
}


def _build_mysql_url(prefix: str, defaults: Dict[str, str]) -> str:
    """Construye la URL de conexión a MySQL usando env con fallback a defaults.

    Prefijo esperado, por ejemplo: LOGIN_DB o APP_DB.
    Variables soportadas: {PREFIX}_{HOST,USER,PASSWORD,DATABASE,PORT}
    """
    host = os.getenv(f"{prefix}_HOST", defaults["HOST"]).strip()
    user = os.getenv(f"{prefix}_USER", defaults["USER"]).strip()
    password = os.getenv(f"{prefix}_PASSWORD", defaults["PASSWORD"]).strip()
    database = os.getenv(f"{prefix}_DATABASE", defaults["DATABASE"]).strip()
    port = os.getenv(f"{prefix}_PORT", defaults.get("PORT", "3306")).strip()

    # Asegurar que usuario/contraseña estén codificados para URL
    user_q = quote_plus(user)
    pass_q = quote_plus(password)

    return f"mysql+mysqlconnector://{user_q}:{pass_q}@{host}:{port}/{database}"


LOGIN_DB_URL = _build_mysql_url("LOGIN_DB", DEFAULT_LOGIN_DB)
APP_DB_URL = _build_mysql_url("APP_DB", DEFAULT_APP_DB)

login_engine = create_engine(LOGIN_DB_URL, pool_pre_ping=True)
app_engine = create_engine(APP_DB_URL, pool_pre_ping=True)


def hash_password_with_salt(password: str, salt: Optional[str] = None) -> Dict[str, str]:
    if salt is None:
        # 32 hex chars = 16 bytes
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return {"salt": salt, "hash": dk.hex()}


def verify_password(salt: str, stored_hash: str, provided_password: str) -> bool:
    calc = hash_password_with_salt(provided_password, salt)["hash"]
    return calc == stored_hash


def create_token(payload: Dict[str, Any]) -> str:
    to_encode = payload.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRES_HOURS)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


# =========================
# Modelos de request/response
# =========================


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


class ConsultaResponse(BaseModel):
    count: int
    results: List[Dict[str, Any]]


# =========================
# App y seguridad
# =========================

app = FastAPI(title=APP_TITLE)
auth_scheme = HTTPBearer(auto_error=False)


def require_db_engines():
    # Con defaults "quemados" y overrides por env, los engines siempre deberían existir.
    # Esta validación se mantiene por si en el futuro se cambia el flujo de inicialización.
    if not login_engine or not app_engine:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "No se pudieron inicializar los engines de base de datos. "
                "Verifique variables LOGIN_DB_* y APP_DB_* o los valores por defecto."
            ),
        )


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_scheme)) -> Dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta token Bearer")
    token = credentials.credentials
    data = decode_token(token)
    return data


def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    # Regla simple: admin si username == 'admin'
    if user.get("username") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
    return user


# =========================
# Endpoints
# =========================


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": APP_TITLE}


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    require_db_engines()
    q = text(
        """
        SELECT username, password_hash, sal, activo, nombre_completo
        FROM usuarios
        WHERE username = :username
        """
    )
    with login_engine.connect() as conn:
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


@app.post("/auth/change-password")
def change_password(body: ChangePasswordRequest, user: Dict[str, Any] = Depends(get_current_user)):
    require_db_engines()
    username = user["username"]

    # Obtener hash actual
    with login_engine.connect() as conn:
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


@app.post("/auth/register")
def register_user(body: RegisterUserRequest, _: Dict[str, Any] = Depends(require_admin)):
    require_db_engines()
    with login_engine.connect() as conn:
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


@app.get("/consulta", response_model=ConsultaResponse)
def consulta(documento: str = Query(..., min_length=6, max_length=15), _: Dict[str, Any] = Depends(get_current_user)):
    require_db_engines()
    q = text("SELECT * FROM vw_matricula_cero_2025_2 WHERE documento = :doc")
    with app_engine.connect() as conn:
        rows = conn.execute(q, {"doc": documento}).fetchall()

    results: List[Dict[str, Any]] = [dict(r._mapping) for r in rows]
    return ConsultaResponse(count=len(results), results=results)

