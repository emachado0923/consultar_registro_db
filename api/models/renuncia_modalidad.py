from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class RenunciaModalidadBase(SQLModel):
    docconvfondo: str = Field(max_length=50)
    documento: str = Field(max_length=50)
    convocatoria: str = Field(max_length=6)
    fondo_sapiencia: str = Field(max_length=10)
    modalidad_a_la_cual_renuncia: str = Field(max_length=100)
    radicado_pqrs: str = Field(max_length=100)


class RenunciaModalidad(RenunciaModalidadBase, table=True):
    __tablename__ = "renuncia_modalidad"

    id: Optional[int] = Field(default=None, primary_key=True)
    responsable_registro: str = Field(max_length=100)
    fecha_registro: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={
            "server_default": "CURRENT_TIMESTAMP",
            "onupdate": "CURRENT_TIMESTAMP",
        },
    )


class RenunciaModalidadCreate(RenunciaModalidadBase):
    pass
