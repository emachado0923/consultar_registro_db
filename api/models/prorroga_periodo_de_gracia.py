from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ProrrogaPeriodoDeGraciaBase(SQLModel):
    docconvfondo: str = Field(max_length=50)
    documento: str = Field(max_length=50)
    convocatoria: str = Field(max_length=6)
    fondo_sapiencia: str = Field(max_length=10)
    fecha_fin_prorroga: date
    radicado_pqrs: str = Field(max_length=100)


class ProrrogaPeriodoDeGracia(ProrrogaPeriodoDeGraciaBase, table=True):
    __tablename__ = "prorroga_periodo_de_gracia"

    id: Optional[int] = Field(default=None, primary_key=True)
    responsable_registro: str = Field(max_length=100)
    fecha_registro: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={
            "server_default": "CURRENT_TIMESTAMP",
            "onupdate": "CURRENT_TIMESTAMP",
        },
    )


class ProrrogaPeriodoDeGraciaCreate(ProrrogaPeriodoDeGraciaBase):
    pass
