from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..core.database import get_session_analitica
from ..models.programas_preg_posg import (
    ProgramasPregPosg,
    ProgramasPregPosgCreate,
    ProgramasPregPosgUpdate,
)
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/programas-preg-posg", tags=["Programas Preg Posg"])


@router.get("/", response_model=List[ProgramasPregPosg], summary="Listar todos los programas")
def list_programas(session: SessionDep):
    """Devuelve todos los registros (considera paginación si hay muchos)."""
    statement = select(ProgramasPregPosg)
    results = session.exec(statement).all()
    return results


@router.get("/{item_id}", response_model=ProgramasPregPosg, summary="Obtener programa por id")
def get_programa(item_id: int, session: SessionDep, _: Dict[str, Any] = Depends(get_current_user)):
    item = session.get(ProgramasPregPosg, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Programa no encontrado")
    return item


@router.get("/by-ies/{id_ies}", response_model=List[ProgramasPregPosg], summary="Obtener programas asociados a una IES (por id_ies)")
def get_programas_by_ies(id_ies: str, session: SessionDep, _: Dict[str, Any] = Depends(get_current_user)):
    """
    Devuelve solo los programas cuyo campo `id_ies` coincide con el parámetro.
    Útil para mostrar los programas de una IES concreta.
    """
    statement = select(ProgramasPregPosg).where(ProgramasPregPosg.id_ies == id_ies)
    results = session.exec(statement).all()
    return results


@router.post("/agregar", response_model=ProgramasPregPosg, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo programa")
def create_programa(
    data: ProgramasPregPosgCreate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> ProgramasPregPosg:
    new_item = ProgramasPregPosg.from_orm(data)
    try:
        session.add(new_item)
        session.commit()
        session.refresh(new_item)
        return new_item
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Conflicto de integridad al crear el registro.")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")


@router.put("/{item_id}", response_model=ProgramasPregPosg, summary="Actualizar programa por id")
def update_programa(
    item_id: int,
    data: ProgramasPregPosgUpdate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> ProgramasPregPosg:
    db_item = session.get(ProgramasPregPosg, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Programa no encontrado")

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)

    try:
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        return db_item
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Conflicto de integridad en la actualización.")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar programa por id")
def delete_programa(item_id: int, session: SessionDep, user: Dict[str, Any] = Depends(get_current_user)):
    db_item = session.get(ProgramasPregPosg, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Programa no encontrado")
    try:
        session.delete(db_item)
        session.commit()
        return None
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
