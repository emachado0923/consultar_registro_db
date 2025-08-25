from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..core.database import get_session_analitica
from ..models.informacion_programas_academicos import (
    InformacionProgramasAcademicos,
    InformacionProgramasAcademicosUpdate,
)
from .auth import get_current_user


SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/informacion-programas-academicos", tags=["Información Académica"])


@router.get("/", response_model=list[InformacionProgramasAcademicos])
def read_informacion_programas_academicos(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
    _: Dict[str, Any] = Depends(get_current_user),
) -> list[InformacionProgramasAcademicos]:
    items = session.exec(select(InformacionProgramasAcademicos).offset(offset).limit(limit)).all()
    return items


@router.get("/{docconvfondo}", response_model=InformacionProgramasAcademicos)
def get_informacion_programas_academicos(
    docconvfondo: str,
    session: SessionDep,
    _: Dict[str, Any] = Depends(get_current_user),
) -> InformacionProgramasAcademicos:
    item = session.get(InformacionProgramasAcademicos, docconvfondo)
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return item


@router.post("/actualizar", response_model=InformacionProgramasAcademicos)
def update_informacion_programas_academicos(
    data: InformacionProgramasAcademicosUpdate,
    session: SessionDep,
    docconvfondo: str = Query(...),
    user: Dict[str, Any] = Depends(get_current_user),
) -> InformacionProgramasAcademicos:
    item = session.get(InformacionProgramasAcademicos, docconvfondo)
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    # Ignore client-provided responsable_actualizacion; set it from authenticated user
    update_data = data.dict(exclude_unset=True, exclude={"responsable_actualizacion"})
    for key, value in update_data.items():
        setattr(item, key, value)
    item.responsable_actualizacion = user.get("full_name", "N/A")
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
