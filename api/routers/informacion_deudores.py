from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..core.database import get_session_analitica
from ..models.informacion_deudores import (
    InformacionDeudores,
    InformacionDeudoresUpdate,
)
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/informacion-deudores", tags=["Información de Deudores"])


@router.get(
    "/",
    response_model=List[InformacionDeudores],
    summary="Leer información de deudores con paginación",
)
def get_informacion_deudores(
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
) -> List[InformacionDeudores]:
    """
    Obtiene una lista paginada de la información de los deudores.
    """
    items = session.exec(select(InformacionDeudores).offset(offset).limit(limit)).all()
    return items


@router.post(
    "/actualizar",
    response_model=InformacionDeudores,
    summary="Actualizar información de un deudor",
)
def update_informacion_deudor(
    idconvfondo: str,
    data: InformacionDeudoresUpdate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> InformacionDeudores:
    """
    Actualiza la información de un deudor específico.
    """
    db_item = session.get(InformacionDeudores, idconvfondo)
    if not db_item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)

    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item
