from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..core.database import get_session_analitica
from ..models.renuncia_modalidad import (
    RenunciaModalidad,
    RenunciaModalidadCreate,
)
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/renuncia-modalidad", tags=["Renuncia Modalidad"])


@router.post(
    "/agregar",
    response_model=RenunciaModalidad,
    summary="Agregar una nueva renuncia de modalidad",
)
def add_renuncia_modalidad(
    data: RenunciaModalidadCreate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> RenunciaModalidad:
    responsable_registro = user.get("full_name", "N/A")
    new_item = RenunciaModalidad.from_orm(
        data, {"responsable_registro": responsable_registro}
    )
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    return new_item
