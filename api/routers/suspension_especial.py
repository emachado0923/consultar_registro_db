from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..core.database import get_session_analitica
from ..models.suspension_especial import (
    SuspensionEspecial,
    SuspensionEspecialCreate,
)
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/suspension-especial", tags=["Suspensión Especial"])


@router.post("/agregar", response_model=SuspensionEspecial)
def add_suspension_especial(
    data: SuspensionEspecialCreate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> SuspensionEspecial:
    responsable_creacion = user.get("full_name", "N/A")
    new_item = SuspensionEspecial.from_orm(
        data, {"responsable_creacion": responsable_creacion}
    )
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    return new_item
