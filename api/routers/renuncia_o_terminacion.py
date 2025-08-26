from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..core.database import get_session_analitica
from ..models.renuncia_o_terminacion import (
    RenunciaOTerminacion,
    RenunciaOTerminacionCreate,
)
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/renuncia-o-terminacion", tags=["Renuncia o Terminación"])


@router.post("/agregar", response_model=RenunciaOTerminacion)
def add_renuncia_o_terminacion(
    data: RenunciaOTerminacionCreate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> RenunciaOTerminacion:
    responsable_creacion = user.get("full_name", "N/A")
    new_item = RenunciaOTerminacion.from_orm(
        data, {"responsable_creacion": responsable_creacion}
    )
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    return new_item
