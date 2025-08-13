import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus


# Valores por defecto ("quemados"). Se pueden sobreescribir por .env/variables de entorno.
DEFAULT_ANALITICA_DB = {
    #"HOST": "10.124.80.4",
    "HOST": "REDACTED",
    "USER": "analitica",
    "PASSWORD": "REDACTED",
    "DATABASE": "analitica_fondos",
    "PORT": "3306",
}

DEFAULT_CONVOCATORIA_DB = {
    #"HOST": "10.124.80.4",
    "HOST": "REDACTED",
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


ANALITICA_DB_URL = _build_mysql_url("LOGIN_DB", DEFAULT_ANALITICA_DB)
CONVOCATORIA_DB_URL = _build_mysql_url("APP_DB", DEFAULT_CONVOCATORIA_DB)

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_THIS_PLEASE")
JWT_EXPIRES_HOURS = 24 * 30 * 12  # 1 año
