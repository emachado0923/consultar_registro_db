from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from api.core.database import engine_analitica
from api.core.security_seguimiento import (
    create_token_seguimiento,
    decode_token_seguimiento,
    hash_password,
    verify_password,
)
from api.models.seguimiento_auth import (
    CambiarPasswordPrimerLoginRequest,
    LoginSeguimientoRequest,
    TokenSeguimientoResponse,
)

router = APIRouter(prefix="/seguimiento/auth", tags=["Seguimiento · Auth"])
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_seguimiento(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Dict[str, Any]:
    """Dependencia de autenticación para todos los endpoints de /seguimiento/*."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta token Bearer")
    return decode_token_seguimiento(credentials.credentials)


def require_rol(*roles_permitidos: str):
    """
    Dependencia factory: uso `Depends(require_rol("ADMIN"))` o
    `Depends(require_rol("ADMIN", "LMC", "AST"))`. Replica los checks que hoy
    hace la app Streamlit por rol (ej. rol_activo != "DIRECTORA").
    """
    def _checker(user: Dict[str, Any] = Depends(get_current_user_seguimiento)) -> Dict[str, Any]:
        if user.get("rol") not in roles_permitidos:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para este rol")
        return user
    return _checker


@router.post("/login", response_model=TokenSeguimientoResponse, summary="Iniciar sesión (Seguimiento Convenios MC)")
def login(body: LoginSeguimientoRequest):
    q = text("""
        SELECT id, nombre, usuario, password_hash, rol, activo, primer_login
        FROM usuarios_seg_proceso_mc
        WHERE usuario = :usuario
    """)
    with engine_analitica.connect() as conn:
        row = conn.execute(q, {"usuario": body.usuario}).fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

    uid, nombre, usuario, password_hash, rol, activo, primer_login = row

    if not activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo. Contacta al administrador.")
    if not verify_password(body.password, password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta")

    token = create_token_seguimiento(usuario_id=uid, usuario=usuario, nombre=nombre, rol=rol)
    return TokenSeguimientoResponse(
        access_token=token,
        usuario={"id": uid, "nombre": nombre, "usuario": usuario, "rol": rol},
        primer_login=bool(primer_login),
    )


@router.post("/cambiar-password", summary="Cambiar contraseña (obligatorio en el primer login)")
def cambiar_password(
    body: CambiarPasswordPrimerLoginRequest,
    user: Dict[str, Any] = Depends(get_current_user_seguimiento),
):
    nuevo_hash = hash_password(body.nueva_password)
    with engine_analitica.connect() as conn:
        conn.execute(
            text("UPDATE usuarios_seg_proceso_mc SET password_hash=:h, primer_login=0 WHERE id=:id"),
            {"h": nuevo_hash, "id": user["usuario_id"]},
        )
        conn.commit()
    return {"status": "ok"}
