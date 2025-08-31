from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..core.database import get_session_analitica
from ..models.suspension_temporal import (
    SuspensionTemporal,
    SuspensionTemporalCreate,
)
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/suspension-temporal", tags=["Suspensión Temporal"])


@router.post("/agregar", response_model=SuspensionTemporal, summary="Agregar una nueva suspensión temporal")
def add_suspension_temporal(
    data: SuspensionTemporalCreate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> SuspensionTemporal:
    responsable_creacion = user.get("full_name", "N/A")
    new_item = SuspensionTemporal.from_orm(
        data, {"responsable_creacion": responsable_creacion}
    )
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    return new_item
