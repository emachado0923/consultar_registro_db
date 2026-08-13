"""
Helpers de autenticación específicos del módulo Seguimiento Convenios MC.

Se mantienen separados de api/core/security.py (que es el login genérico de
la API, con hashing pbkdf2+sal sobre la tabla `usuarios`) porque
usuarios_seg_proceso_mc usa bcrypt — exactamente como ya lo hacía la app
Streamlit — y son dos universos de usuarios distintos.

create_token()/decode_token() de api/core/security.py SÍ se reutilizan tal
cual (son JWT genéricos); aquí solo se agrega el claim "modulo": "seguimiento"
para que un token de este módulo no sirva para autorizar los endpoints del
login genérico de la API, ni viceversa.
"""
from typing import Any, Dict

import bcrypt
from fastapi import HTTPException, status

from api.core.security import create_token, decode_token

MODULO_CLAIM = "seguimiento"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_token_seguimiento(usuario_id: int, usuario: str, nombre: str, rol: str) -> str:
    return create_token({
        "modulo": MODULO_CLAIM,
        "usuario_id": usuario_id,
        "usuario": usuario,
        "nombre": nombre,
        "rol": rol,
    })


def decode_token_seguimiento(token: str) -> Dict[str, Any]:
    data = decode_token(token)
    if data.get("modulo") != MODULO_CLAIM:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no válido para el módulo de Seguimiento",
        )
    return data
