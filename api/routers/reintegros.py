from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
import logging
import traceback

logger = logging.getLogger(__name__)

from api.core.database import engine_analitica
from api.models.reintegros import (
    Reintegros,
    ReintegrosCreate,
    ReintegrosUpdate,
    ReintegroResponse,
)
from api.routers.auth import get_current_user

router = APIRouter()


@router.get(
    "/consulta/",
    response_model=List[Reintegros],
    tags=["Reintegros"],
    summary="Consultar reintegros por beneficiario o documento",
)
def get_reintegros(
    beneficiario: str = Query(None, min_length=1, max_length=100),
    documento: str = Query(None, min_length=1, max_length=20),
    _: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        statement = select(Reintegros)
        
        if beneficiario:
            statement = statement.where(Reintegros.beneficiario.contains(beneficiario))
        if documento:
            statement = statement.where(Reintegros.documento == documento)
            
        statement = statement.order_by(Reintegros.fecha_inicio_proceso.desc())
        results = session.exec(statement).all()
        return results


@router.get(
    "/consulta/{reintegro_id}",
    response_model=Reintegros,
    tags=["Reintegros"],
    summary="Consultar un reintegro por ID",
)
def get_reintegro_by_id(
    reintegro_id: int,
    _: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        reintegro = session.get(Reintegros, reintegro_id)
        if not reintegro:
            raise HTTPException(status_code=404, detail="Reintegro no encontrado")
        return reintegro


@router.post(
    "/agrega-tabla-formulario/",
    response_model=ReintegroResponse,
    tags=["Reintegros"],
    summary="Crear un nuevo reintegro",
)
def create_reintegro(
    reintegro: ReintegrosCreate,
    user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        logger.info(f"Intentando crear reintegro para documento: {reintegro.documento}")
        
        with Session(engine_analitica) as session:
            reintegro_data = reintegro.model_dump()
            db_reintegro = Reintegros(**reintegro_data)
            session.add(db_reintegro)
            session.commit()
            session.refresh(db_reintegro)
            
            logger.info(f"Reintegro creado exitosamente con ID: {db_reintegro.id}")
            
            response_data = ReintegroResponse(
                id=db_reintegro.id,
                beneficiario=db_reintegro.beneficiario,
                ies=db_reintegro.ies,
                documento=db_reintegro.documento,
                monto_girado=db_reintegro.monto_girado,
                monto_girado_sostenimiento=db_reintegro.monto_girado_sostenimiento,
                monto_girado_matricula=db_reintegro.monto_girado_matricula,
                monto_reintegro=db_reintegro.monto_reintegro,
                motivo_reintegro=db_reintegro.motivo_reintegro,
                modalidad_reintegro=db_reintegro.modalidad_reintegro,
                fecha_inicio_proceso=db_reintegro.fecha_inicio_proceso,
                estado_correo=db_reintegro.estado_correo,
                certificado=db_reintegro.certificado,
                estado_fiducia=db_reintegro.estado_fiducia,
                fecha_efectuado=db_reintegro.fecha_efectuado
            )
            
            return response_data
            
    except Exception as e:
        logger.error(f"Error creando reintegro: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.put(
    "/actualiza-tabla-formulario/{reintegro_id}",
    response_model=Reintegros,
    tags=["Reintegros"],
    summary="Actualizar un reintegro existente",
)
def update_reintegro(
    reintegro_id: int,
    reintegro: ReintegrosUpdate,
    user: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        db_reintegro = session.get(Reintegros, reintegro_id)
        if not db_reintegro:
            raise HTTPException(status_code=404, detail="Reintegro no encontrado")
        
        reintegro_data = reintegro.model_dump(exclude_unset=True)
        for key, value in reintegro_data.items():
            setattr(db_reintegro, key, value)
        
        session.add(db_reintegro)
        session.commit()
        session.refresh(db_reintegro)
        return db_reintegro


@router.delete(
    "/elimina-tabla-formulario/{reintegro_id}",
    tags=["Reintegros"],
    summary="Eliminar un reintegro",
)
def delete_reintegro(
    reintegro_id: int,
    user: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        reintegro = session.get(Reintegros, reintegro_id)
        if not reintegro:
            raise HTTPException(status_code=404, detail="Reintegro no encontrado")
        
        session.delete(reintegro)
        session.commit()
        return {
            "status": "ok",
            "message": "Reintegro eliminado exitosamente"
        }


class DocumentoReintegro(BaseModel):
    documento: str


@router.get(
    "/consulta-por-fecha/",
    response_model=List[Reintegros],
    tags=["Reintegros"],
    summary="Consultar reintegros por rango de fechas",
)
def get_reintegros_por_fecha(
    fecha_desde: str = Query(..., description="Fecha inicial (YYYY-MM-DD)"),
    fecha_hasta: str = Query(..., description="Fecha final (YYYY-MM-DD)"),
    _: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        statement = select(Reintegros).where(
            Reintegros.fecha_inicio_proceso >= fecha_desde,
            Reintegros.fecha_inicio_proceso <= fecha_hasta
        ).order_by(Reintegros.fecha_inicio_proceso.desc())
        
        results = session.exec(statement).all()
        return results