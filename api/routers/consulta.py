from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from api.core.database import engine_convocatoria, engine_analitica
from api.models.consulta import ConsultaResponse
from api.routers.auth import get_current_user

router = APIRouter()


@router.get("/formulario-mc", response_model=ConsultaResponse, tags=["Consulta"])
def consulta(documento: str = Query(..., min_length=6, max_length=15), _: Dict[str, Any] = Depends(get_current_user)):
    q = text("SELECT * FROM vw_matricula_cero_2025_2 WHERE documento = :doc")
    with engine_convocatoria.connect() as conn:
        rows = conn.execute(q, {"doc": documento}).fetchall()

    results: List[Dict[str, Any]] = [dict(r._mapping) for r in rows]
    return ConsultaResponse(count=len(results), results=results)


@router.get("/consulta-nombre", response_model=ConsultaResponse, tags=["Consulta"])
def consulta(documento: str = Query(..., min_length=6, max_length=15), _: Dict[str, Any] = Depends(get_current_user)):
    q = text("SELECT id_usuario, primerNombre, segundoNombre, primerApellido, segundoApellido FROM login_usuario WHERE documento = :doc")
    with engine_convocatoria.connect() as conn:
        rows = conn.execute(q, {"doc": documento}).fetchall()
    
    results: List[Dict[str, Any]] = [dict(r._mapping) for r in rows]
    return ConsultaResponse(count=len(results), results=results)


@router.get("/existe-tabla-habilitados-renovar", response_model=ConsultaResponse, tags=["Consulta"])
def consulta(documento: str = Query(...,min_length=3, max_length=20), _: Dict[str, Any] = Depends(get_current_user)):
    q = text("SELECT COUNT(*) AS existe FROM fondos_habilitados_renovar WHERE documento = :d")
    with engine_convocatoria.connect() as conn:
        rows = conn.execute(q, {"d": documento}).fetchall()
    results: List[Dict[str, Any]] = [dict(r._mapping) for r in rows]
    return ConsultaResponse(count=len(results), results=results)



@router.get("/fondos", tags=["Consulta"])
def consulta(documento: str = Query(..., min_length=6, max_length=15), _: Dict[str, Any] = Depends(get_current_user)):
    q = text("SELECT * FROM vw_informacion_beneficiario WHERE documento = :doc")

    with engine_analitica.connect() as conn:
        
        rows = conn.execute(q, {"doc": documento}).fetchall()

    results_from_db: List[Dict[str, Any]] = [dict(r._mapping) for r in rows]

    if not results_from_db:
        return {}

    aggregated_result = {
        "nombre": results_from_db[0].get("nombre_completo"),
        "id_usuario": results_from_db[0].get("id_usuario"),
        "convocatoria": [r.get("convocatoria") for r in results_from_db],
        "fondo": [r.get("fondo_sapiencia") for r in results_from_db],
        "tiene_varios_registros": results_from_db[0].get("tiene_varios_fondos"),
    }
    
    return aggregated_result
