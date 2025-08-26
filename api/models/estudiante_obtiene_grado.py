from datetime import date, datetime
from typing import Optional

from sqlalchemy import text
from sqlmodel import Field, SQLModel


class EstudianteObtieneGrado(SQLModel, table=True):
    __tablename__ = "estudiante_obtiene_grado"

    docconvfondo: str = Field(primary_key=True, max_length=100)
    documento: str = Field(max_length=100)
    convocatoria: Optional[str] = Field(default=None, max_length=100)
    fondo_sapiencia: str = Field(max_length=100)
    periodo_grado: Optional[str] = Field(default=None, max_length=100)
    fecha_grado: Optional[date] = Field(default=None)
    fecha_creacion: Optional[datetime] = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )
    responsable_creacion: str = Field(max_length=100)


class EstudianteObtieneGradoCreate(SQLModel):
    docconvfondo: str
    documento: str
    convocatoria: Optional[str] = None
    fondo_sapiencia: str
    periodo_grado: Optional[str] = None
    fecha_grado: Optional[date] = None
