from datetime import datetime, timedelta
import hashlib
import os
from typing import Any, Dict, Optional

import jwt
from fastapi import HTTPException, status

from api.core.config import JWT_ALGORITHM, JWT_SECRET, JWT_EXPIRES_HOURS


def hash_password_with_salt(password: str, salt: Optional[str] = None) -> Dict[str, str]:
    if salt is None:
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
