from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class ActividadConvenioSeguimiento(SQLModel, table=True):
    """Tabla actividades_convenio_seg_mc (ya existente, esquema sin cambios)."""
    __tablename__ = "actividades_convenio_seg_mc"

    id: Optional[int] = Field(default=None, primary_key=True)
    convenio_id: int = Field(foreign_key="convenios_seg_proceso_mc.id")
    convenio_periodo_id: int = Field(foreign_key="convenio_periodos_seg_mc.id")
    actividad_base_id: int = Field(foreign_key="actividades_base_seg_mc.id")
    estado: Optional[str] = Field(default="Pendiente", max_length=20)
    porcentaje_avance: Optional[int] = Field(default=0)
    fecha_inicio_real: Optional[date] = None
    fecha_completado: Optional[date] = None
    no_aplica: Optional[int] = Field(default=0)
    responsable_id: Optional[int] = Field(default=None, foreign_key="usuarios_seg_proceso_mc.id")
    ultimo_comentario: Optional[str] = None
    fecha_recordatorio: Optional[date] = None
    nota_recordatorio: Optional[str] = None
    recordatorio_enviado: Optional[int] = Field(default=0)
    ultima_actualizacion: Optional[datetime] = None


class ActividadPeriodoOut(BaseModel):
    """Fila de actividad para GET /seguimiento/periodos/{id}/actividades — incluye datos del catálogo unidos."""
    actividad_base_id: int
    nombre: str
    subcategoria: str
    subcategoria_orden: int
    orden: int
    es_relevante: bool
    tiene_fecha_limite: bool
    actividad_convenio_id: Optional[int] = None
    estado: str = "Pendiente"
    porcentaje_avance: int = 0
    ultimo_comentario: Optional[str] = None
    ultima_actualizacion: Optional[datetime] = None
    responsable_nombre: Optional[str] = None
    responsable_rol: Optional[str] = None
    fecha_completado: Optional[date] = None
    no_aplica: bool = False
    fecha_recordatorio: Optional[date] = None
    nota_recordatorio: Optional[str] = None


class AvanceUpdateRequest(BaseModel):
    """Equivalente a guardar_avance() de la app Streamlit."""
    porcentaje_avance: int = Field(ge=0, le=100)
    comentario: Optional[str] = None
    fecha_manual: Optional[date] = None
    fecha_recordatorio: Optional[date] = None
    nota_recordatorio: Optional[str] = None


class NoAplicaRequest(BaseModel):
    """Equivalente a marcar_no_aplica(). no_aplica=True guarda la actividad como
    Completada/100%; no_aplica=False la revierte a Pendiente/0%."""
    no_aplica: bool


class RecordatorioUpdateRequest(BaseModel):
    fecha_recordatorio: Optional[date] = None
    nota_recordatorio: Optional[str] = None


class AvanceResponse(BaseModel):
    avanzo_estado_convenio: bool
    codigo_convenio: Optional[str] = None
    nuevo_estado_convenio: Optional[str] = None
