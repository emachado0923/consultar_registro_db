from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..core.database import get_session_analitica
from ..models.seguimiento_ies import IESSeguimiento, IESSeguimientoCreate, IESSeguimientoUpdate
from .seguimiento_auth import get_current_user_seguimiento, require_rol

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/seguimiento/ies", tags=["Seguimiento · IES"])


@router.get("/", response_model=List[IESSeguimiento], summary="Listar IES activas")
def list_ies(session: SessionDep, _: Dict[str, Any] = Depends(get_current_user_seguimiento)):
    statement = select(IESSeguimiento).where(IESSeguimiento.activa == 1).order_by(IESSeguimiento.nombre)
    return session.exec(statement).all()


@router.post("/", response_model=IESSeguimiento, status_code=status.HTTP_201_CREATED, summary="Registrar nueva IES (solo ADMIN)")
def create_ies(
    data: IESSeguimientoCreate,
    session: SessionDep,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
) -> IESSeguimiento:
    nueva = IESSeguimiento.from_orm(data)
    try:
        session.add(nueva)
        session.commit()
        session.refresh(nueva)
        return nueva
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Ya existe una IES con ese nombre.")


@router.put("/{ies_id}", response_model=IESSeguimiento, summary="Editar una IES (solo ADMIN)")
def update_ies(
    ies_id: int,
    data: IESSeguimientoUpdate,
    session: SessionDep,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
) -> IESSeguimiento:
    db_item = session.get(IESSeguimiento, ies_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="IES no encontrada")
    for key, value in data.dict(exclude_unset=True).items():
        setattr(db_item, key, value)
    try:
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        return db_item
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Ya existe una IES con ese nombre.")
