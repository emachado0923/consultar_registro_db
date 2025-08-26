from datetime import date, datetime
from typing import Optional

from sqlalchemy import text
from sqlmodel import Field, SQLModel


class EstudianteObtieneGrado(SQLModel, table=True):
    __tablename__ = "estudiante_obtiene_grado"

    documento: str = Field(primary_key=True, max_length=100)
    fondo_sapiencia: str = Field(primary_key=True, max_length=100)
    ies_grado: str = Field(max_length=100)
    periodo_grado: Optional[str] = Field(default=None, max_length=100)
    fecha_grado: Optional[date] = Field(default=None)
    fecha_actualizacion: Optional[datetime] = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )
    responsable_actualizacion: str = Field(max_length=100)


class EstudianteObtieneGradoCreate(SQLModel):
    documento: str
    fondo_sapiencia: str
    ies_grado: str
    periodo_grado: Optional[str] = None
    fecha_grado: Optional[date] = None
