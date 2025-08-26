from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import text

from api.core.database import engine_analitica
from api.models.changelog import ChangeLogRequest
from api.routers.auth import get_current_user

router = APIRouter()


@router.post("/changelog", tags=["ChangeLog"], summary="Crear un registro de cambio")
def create_change_log(body: ChangeLogRequest, user: Dict[str, Any] = Depends(get_current_user)):
    responsable_cambio = user.get("full_name", "N/A")
    with engine_analitica.connect() as conn:
        conn.execute(
            text(
                """
                INSERT INTO change_log_fondos (tipo_cambio, documento_beneficiario_cambio, responsable_cambio)
                VALUES (:tipo_cambio, :documento_beneficiario_cambio, :responsable_cambio)
                """
            ),
            {
                "tipo_cambio": body.tipo_cambio,
                "documento_beneficiario_cambio": body.documento_beneficiario_cambio,
                "responsable_cambio": responsable_cambio,
            },
        )
        conn.commit()
    return {"status": "ok"}
