from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class HistorialActividadSeguimiento(SQLModel, table=True):
    """Tabla historial_actividades_seg_mc (ya existente, esquema sin cambios). Solo lectura vía API."""
    __tablename__ = "historial_actividades_seg_mc"

    id: Optional[int] = Field(default=None, primary_key=True)
    actividad_convenio_id: int = Field(foreign_key="actividades_convenio_seg_mc.id")
    fecha_cambio: Optional[datetime] = None
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuarios_seg_proceso_mc.id")
    usuario_nombre: Optional[str] = Field(default=None, max_length=100)
    estado_anterior: Optional[str] = Field(default=None, max_length=20)
    estado_nuevo: Optional[str] = Field(default=None, max_length=20)
    porcentaje_anterior: Optional[int] = None
    porcentaje_nuevo: Optional[int] = None
    comentario: Optional[str] = None
