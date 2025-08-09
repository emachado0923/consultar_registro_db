from typing import Annotated, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from ..core.database import get_session_analitica
from ..models.informacion_personal import (
    InformacionPersonal,
    InformacionPersonalUpdate,
)
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/informacion-personal", tags=["informacion_personal"])

@router.post("/", response_model=InformacionPersonal)
def create_informacion_personal(
    item: InformacionPersonal,
    session: SessionDep,
    _: Dict[str, Any] = Depends(get_current_user),
) -> InformacionPersonal:
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@router.get("/", response_model=list[InformacionPersonal])
def read_informacion_personal(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
    _: Dict[str, Any] = Depends(get_current_user),
) -> list[InformacionPersonal]:
    items = session.exec(select(InformacionPersonal).offset(offset).limit(limit)).all()
    return items

@router.patch("/{docconvfondo}", response_model=InformacionPersonal)
def update_informacion_personal(
    docconvfondo: str,
    data: InformacionPersonalUpdate,
    session: SessionDep,
    _: Dict[str, Any] = Depends(get_current_user),
) -> InformacionPersonal:
    item = session.get(InformacionPersonal, docconvfondo)
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@router.delete("/{docconvfondo}")
def delete_informacion_personal(
    docconvfondo: str,
    session: SessionDep,
    _: Dict[str, Any] = Depends(get_current_user),
):
    item = session.get(InformacionPersonal, docconvfondo)
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    session.delete(item)
    session.commit()
    return {"ok": True}
