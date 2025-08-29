from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..core.database import get_session_analitica
from ..models.prorroga_periodo_de_gracia import (
    ProrrogaPeriodoDeGracia,
    ProrrogaPeriodoDeGraciaCreate,
)
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(
    prefix="/prorroga-periodo-de-gracia", tags=["Prorroga Periodo de Gracia"]
)


@router.post(
    "/agregar",
    response_model=ProrrogaPeriodoDeGracia,
    summary="Agregar una nueva prorroga de periodo de gracia",
)
def add_prorroga_periodo_de_gracia(
    data: ProrrogaPeriodoDeGraciaCreate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> ProrrogaPeriodoDeGracia:
    responsable_registro = user.get("full_name", "N/A")
    new_item = ProrrogaPeriodoDeGracia.from_orm(
        data, {"responsable_registro": responsable_registro}
    )
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    return new_item
