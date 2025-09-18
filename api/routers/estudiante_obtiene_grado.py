from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from ..core.database import get_session_analitica
from ..models.estudiante_obtiene_grado import (
    EstudianteObtieneGrado,
    EstudianteObtieneGradoCreate,
)
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/estudiante-obtiene-grado", tags=["Estudiante Obtiene Grado"])


@router.post("/agregar", response_model=EstudianteObtieneGrado, summary="Agregar un nuevo registro de grado de estudiante")
def add_estudiante_obtiene_grado(
    data: EstudianteObtieneGradoCreate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> EstudianteObtieneGrado:
    responsable_creacion = user.get("full_name", "Usuario desconocido")
    new_item = EstudianteObtieneGrado.from_orm(
        data, {"responsable_creacion": responsable_creacion}
    )
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
