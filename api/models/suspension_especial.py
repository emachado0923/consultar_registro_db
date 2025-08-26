from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class SuspensionEspecialBase(SQLModel):
    docconvfondo: str = Field(max_length=50)
    documento: str = Field(max_length=20)
    convocatoria: str = Field(max_length=6)
    fondo_sapiencia: str = Field(max_length=50)
    periodo_suspension_especial: str = Field(max_length=6)
    motivo_suspension_especial: str = Field(max_length=255)
    radicado_pqrs: Optional[str] = Field(default=None, max_length=30)


class SuspensionEspecial(SuspensionEspecialBase, table=True):
    __tablename__ = "suspension_especial"

    id: Optional[int] = Field(default=None, primary_key=True)
    fecha_creacion: Optional[datetime] = Field(
        default=None, sa_column_kwargs={"server_default": "CURRENT_TIMESTAMP"}
    )
    responsable_creacion: str = Field(max_length=100)


class SuspensionEspecialCreate(SuspensionEspecialBase):
    pass
