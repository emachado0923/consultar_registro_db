from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class IESSeguimiento(SQLModel, table=True):
    """Tabla ies_seg_proceso_mc (ya existente, esquema sin cambios)."""
    __tablename__ = "ies_seg_proceso_mc"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=255, sa_column_kwargs={"unique": True})
    sigla: Optional[str] = Field(default=None, max_length=20)
    tipo_ies: str = Field(default="Distrital", max_length=20)  # Distrital | Departamental
    activa: Optional[int] = Field(default=1)
    creada_en: Optional[datetime] = Field(default=None)


class IESSeguimientoCreate(SQLModel):
    nombre: str
    sigla: Optional[str] = None
    tipo_ies: str = "Distrital"


class IESSeguimientoUpdate(SQLModel):
    nombre: Optional[str] = None
    sigla: Optional[str] = None
    tipo_ies: Optional[str] = None
    activa: Optional[int] = None
