from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from api.core.database import engine_convocatoria
from api.models.consulta import ConsultaResponse
from api.routers.auth import get_current_user

router = APIRouter()


@router.get("/consulta", response_model=ConsultaResponse, tags=["Consulta"])
def consulta(documento: str = Query(..., min_length=6, max_length=15), _: Dict[str, Any] = Depends(get_current_user)):
    q = text("SELECT * FROM vw_matricula_cero_2025_2 WHERE documento = :doc")
    with engine_convocatoria.connect() as conn:
        rows = conn.execute(q, {"doc": documento}).fetchall()

    results: List[Dict[str, Any]] = [dict(r._mapping) for r in rows]
    return ConsultaResponse(count=len(results), results=results)
