from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select

from api.core.database import engine_analitica
from api.models.informacion_cambio_pensum import (
    InformacionCambioPensum,
    InformacionCambioPensumCreate,
    InformacionCambioPensumUpdate,
    InformacionCambioPensumResponse,
)
from api.routers.auth import get_current_user

router = APIRouter()


@router.post(
    "/agrega-tabla-formulario/",
    response_model=InformacionCambioPensumResponse,
    tags=["Información Cambio Pensum"],
    summary="Crear un nuevo registro de cambio de pensum",
)
def create_informacion_cambio_pensum(
    cambio_pensum: InformacionCambioPensumCreate,
    user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        with Session(engine_analitica) as session:
            # Verificar si ya existe el registro
            existing = session.get(InformacionCambioPensum, cambio_pensum.docconvfondo)
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ya existe un registro con el docconvfondo: {cambio_pensum.docconvfondo}"
                )
            
            # Agregar el responsable de actualización desde el usuario autenticado
            cambio_data = cambio_pensum.model_dump()
            cambio_data["responsable_actualizacion"] = user.get("full_name", "N/A")
            
            db_cambio = InformacionCambioPensum(**cambio_data)
            session.add(db_cambio)
            session.commit()
            session.refresh(db_cambio)
            
            # Convertir a modelo de respuesta
            response_data = InformacionCambioPensumResponse(
                docconvfondo=db_cambio.docconvfondo,
                documento=db_cambio.documento,
                convocatoria=db_cambio.convocatoria,
                fondo=db_cambio.fondo,
                ies_actual=db_cambio.ies_actual,
                programa_actual=db_cambio.programa_actual,
                numero_semestres_pensum_anterior=db_cambio.numero_semestres_pensum_anterior,
                numero_semestres_pensum_actual=db_cambio.numero_semestres_pensum_actual,
                numero_creditos_pensum_anterior=db_cambio.numero_creditos_pensum_anterior,
                numero_creditos_pensum_actual=db_cambio.numero_creditos_pensum_actual,
                periodo_efectivo_cambio=db_cambio.periodo_efectivo_cambio,
                radicado_pqrs_cambio=db_cambio.radicado_pqrs_cambio,
                fecha_actualizacion=db_cambio.fecha_actualizacion,
                responsable_actualizacion=db_cambio.responsable_actualizacion
            )
            
            return response_data
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get(
    "/consulta/",
    response_model=List[InformacionCambioPensum],
    tags=["Información Cambio Pensum"],
    summary="Consultar cambios de pensum por documento o convocatoria",
)
def get_cambios_pensum(
    documento: str = Query(None, min_length=1, max_length=20),
    convocatoria: str = Query(None, min_length=1, max_length=20),
    _: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        statement = select(InformacionCambioPensum)
        
        if documento:
            statement = statement.where(InformacionCambioPensum.documento == documento)
        if convocatoria:
            statement = statement.where(InformacionCambioPensum.convocatoria == convocatoria)
            
        statement = statement.order_by(InformacionCambioPensum.fecha_actualizacion.desc())
        results = session.exec(statement).all()
        return results


@router.get(
    "/consulta/{docconvfondo}",
    response_model=InformacionCambioPensum,
    tags=["Información Cambio Pensum"],
    summary="Consultar un cambio de pensum por ID",
)
def get_cambio_pensum_by_id(
    docconvfondo: str,
    _: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        cambio_pensum = session.get(InformacionCambioPensum, docconvfondo)
        if not cambio_pensum:
            raise HTTPException(status_code=404, detail="Registro de cambio de pensum no encontrado")
        return cambio_pensum


@router.put(
    "/actualiza-tabla-formulario/{docconvfondo}",
    response_model=InformacionCambioPensum,
    tags=["Información Cambio Pensum"],
    summary="Actualizar un registro de cambio de pensum",
)
def update_cambio_pensum(
    docconvfondo: str,
    cambio_pensum: InformacionCambioPensumUpdate,
    user: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        db_cambio = session.get(InformacionCambioPensum, docconvfondo)
        if not db_cambio:
            raise HTTPException(status_code=404, detail="Registro de cambio de pensum no encontrado")
        
        cambio_data = cambio_pensum.model_dump(exclude_unset=True)
        # Actualizar el responsable de actualización
        cambio_data["responsable_actualizacion"] = user.get("full_name", "N/A")
        
        for key, value in cambio_data.items():
            setattr(db_cambio, key, value)
        
        session.add(db_cambio)
        session.commit()
        session.refresh(db_cambio)
        return db_cambio


@router.delete(
    "/elimina-tabla-formulario/{docconvfondo}",
    tags=["Información Cambio Pensum"],
    summary="Eliminar un registro de cambio de pensum",
)
def delete_cambio_pensum(
    docconvfondo: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        cambio_pensum = session.get(InformacionCambioPensum, docconvfondo)
        if not cambio_pensum:
            raise HTTPException(status_code=404, detail="Registro de cambio de pensum no encontrado")
        
        session.delete(cambio_pensum)
        session.commit()
        return {
            "status": "ok",
            "message": "Registro de cambio de pensum eliminado exitosamente"
        }


# Endpoint para verificar duplicados antes de crear
@router.get(
    "/verificar-duplicado/{docconvfondo}",
    tags=["Información Cambio Pensum"],
    summary="Verificar si ya existe un registro con el docconvfondo",
)
def verificar_duplicado(
    docconvfondo: str,
    _: Dict[str, Any] = Depends(get_current_user),
):
    with Session(engine_analitica) as session:
        existing = session.get(InformacionCambioPensum, docconvfondo)
        return {
            "existe": existing is not None,
            "docconvfondo": docconvfondo
        }