from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from ..core.database import get_session_analitica
from ..models.renuncia_giros import RenunciaGiros, RenunciaGirosCreate
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/renuncia-giros", tags=["Renuncia Giros"])


@router.post("/agregar", response_model=RenunciaGiros, summary="Agregar un nuevo registro de renuncia a giros")
def add_renuncia_giros(
    data: RenunciaGirosCreate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> RenunciaGiros:
    responsable = user.get("full_name", "Usuario desconocido")
    # Creamos la instancia del modelo de persistencia y añadimos el responsable
    new_item = RenunciaGiros.from_orm(data, {"responsable_registro": responsable})
    session.add(new_item)
    try:
        session.commit()
        session.refresh(new_item)
        return new_item
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="El registro con el docconvfondo proporcionado ya existe.",
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")