from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select, text

from api.core.database import engine_analitica, engine_convocatoria
from api.models.renovaciones_extemporaneas import (
    RenovacionesExtemporaneas,
    RenovacionesExtemporaneasCreate,
)
from api.routers.auth import get_current_user

router = APIRouter()


@router.get(
    "/consulta/",
    response_model=List[RenovacionesExtemporaneas],
    tags=["Renovaciones Extemporaneas"],
)
def get_renovaciones_extemporaneas(
    periodo: str = Query(..., min_length=6, max_length=6),
    _: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        statement = select(RenovacionesExtemporaneas).where(
            RenovacionesExtemporaneas.periodo == periodo
        )
        results = session.exec(statement).all()
        return results


@router.post(
    "/agrega-tabla-formulario/",
    response_model=RenovacionesExtemporaneas,
    tags=["Renovaciones Extemporaneas"],
)
def create_renovacion_extemporanea(
    renovacion: RenovacionesExtemporaneasCreate,
    user: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        renovacion_data = renovacion.model_dump()
        responsable_activacion = user.get("full_name", "N/A")
        db_renovacion = RenovacionesExtemporaneas(
            **renovacion_data, responsable_activacion=responsable_activacion
        )
        session.add(db_renovacion)
        session.commit()
        session.refresh(db_renovacion)
        return db_renovacion


class Documento(BaseModel):
    documento: int


@router.post(
    "/agrega-tabla-ti/",
    tags=["Renovaciones Extemporaneas"],
)
def agrega_tabla_ti(
    item: Documento,
    _: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_convocatoria) as session:
        try:
            query = text(
                """
                INSERT INTO fondos_habilitados_renovar (
                    documento, efe, fa, ren_mb, leg_mb, pp, epm, dpt,
                    ren_mb_ext, pp_ext, epm_ext, efe_ext, fa_ext, dpt_ext,
                    pre_mb, add_periodo, ctm, ss
                ) VALUES (
                    :documento, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                )
                """
            )
            session.execute(query, {"documento": item.documento})
            session.commit()
            return {
                "status" : "ok",
                "message": "agregado"
            }
        except Exception as e:
            session.rollback()
            if "duplicate" in str(e).lower():
                return {"status": "error", "message": "duplicado"}
            raise e

