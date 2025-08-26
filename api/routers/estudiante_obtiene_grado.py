from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends
from sqlmodel import Session

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
    responsable_actualizacion = user.get("full_name", "N/A")
    new_item = EstudianteObtieneGrado.from_orm(
        data, {"responsable_actualizacion": responsable_actualizacion}
    )
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    return new_item
