from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..core.database import get_session_analitica
from ..models.ies_preg_posg import IESPregPosg, IESPregPosgCreate, IESPregPosgUpdate
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/ies-preg-posg", tags=["IES Preg Posg"])


@router.get("/", response_model=List[IESPregPosg], summary="Listar todas las IES")
def list_ies(session: SessionDep):
    """
    Devuelve la lista completa de registros de ies_preg_posg.
    (Si esperas muchos registros, considera paginación)
    """
    statement = select(IESPregPosg)
    results = session.exec(statement).all()
    return results


# @router.get("/{item_id}", response_model=IESPregPosg, summary="Obtener un registro por id")
# def get_ies(item_id: int, session: SessionDep, _: Dict[str, Any] = Depends(get_current_user)):
#     """
#     Obtiene un registro por su id.
#     Requiere usuario autenticado.
#     """
#     item = session.get(IESPregPosg, item_id)
#     if not item:
#         raise HTTPException(status_code=404, detail="Registro no encontrado")
#     return item


@router.post("/agregar", response_model=IESPregPosg, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo registro")
def create_ies(
    data: IESPregPosgCreate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> IESPregPosg:
    """
    Crea un nuevo registro en ies_preg_posg.
    """
    new_item = IESPregPosg.from_orm(data)
    try:
        session.add(new_item)
        session.commit()
        session.refresh(new_item)
        return new_item
    except IntegrityError:
        session.rollback()
        # No hay constraint único en tu DDL, pero dejamos manejo por si agregas alguno.
        raise HTTPException(status_code=400, detail="Conflicto de integridad al crear el registro.")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")


@router.put("/{item_id}", response_model=IESPregPosg, summary="Actualizar un registro por id")
def update_ies(
    item_id: int,
    data: IESPregPosgUpdate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> IESPregPosg:
    """
    Actualiza parcialmente los campos que se envíen en el payload.
    """
    db_item = session.get(IESPregPosg, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

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


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un registro por id")
def delete_ies(item_id: int, session: SessionDep, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Elimina el registro indicado. Devuelve 204 en caso de éxito.
    """
    db_item = session.get(IESPregPosg, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    try:
        session.delete(db_item)
        session.commit()
        return None
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")