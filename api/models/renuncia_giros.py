from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlmodel import Field, SQLModel


class RenunciaGiros(SQLModel, table=True):
    __tablename__ = "renuncia_giros"

    documento_beneficiario: str = Field(max_length=100)
    motivo_renuncia_giro: str = Field(max_length=100)
    periodo_al_que_renuncia_giro: Optional[str] = Field(default=None, max_length=100)
    radicado_pqrs: Optional[str] = Field(default=None, max_length=100)
    modalidad_renuncia_giro: Optional[str] = Field(default=None, max_length=100)
    a_cuantos_giros_renuncia: int
    id_usuario: int
    fondo_convocatoria: str = Field(alias="fondo-convocatoria", max_length=100)
    giros_pendientes: int
    giros_restantes_renuncia: int
    docconvfondo: str = Field(max_length=100)
    fecha_registro: datetime = Field(
        nullable=False,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )
    responsable_registro: str = Field(max_length=150)


class RenunciaGirosCreate(SQLModel):
    documento_beneficiario: str
    motivo_renuncia_giro: str
    periodo_al_que_renuncia_giro: Optional[str] = None
    radicado_pqrs: Optional[str] = None
    modalidad_renuncia_giro: Optional[str] = None
    a_cuantos_giros_renuncia: int
    id_usuario: int
    fondo_convocatoria: str
    giros_pendientes: int
    giros_restantes_renuncia: int
    docconvfondo: str
    responsable_registro: str