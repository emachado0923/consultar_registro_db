from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel


class ConvenioSeguimiento(SQLModel, table=True):
    """Tabla convenios_seg_proceso_mc (ya existente, esquema sin cambios)."""
    __tablename__ = "convenios_seg_proceso_mc"

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=50, sa_column_kwargs={"unique": True})
    ies_id: int = Field(foreign_key="ies_seg_proceso_mc.id")
    periodo_academico: str = Field(max_length=10)
    estado: Optional[str] = Field(default="En ejecución", max_length=20)
    valor: Optional[Decimal] = Field(default=None)
    adiciones_recursos: Optional[Decimal] = Field(default=None)
    fecha_inicio_convenio: Optional[date] = None
    fecha_fin_convenio: Optional[date] = None
    fecha_limite_liquidacion_voluntaria: Optional[date] = None
    fecha_limite_liquidacion_unilateral: Optional[date] = None
    fecha_limite_liquidacion_judicial: Optional[date] = None
    fecha_vencimiento_poliza: Optional[date] = None
    fecha_firma_director_general: Optional[date] = None
    supervisor: Optional[str] = Field(default=None, max_length=100)
    apoyo_supervision: Optional[str] = Field(default=None, max_length=100)
    observaciones_generales: Optional[str] = None
    creado_en: Optional[datetime] = None
    creado_por: Optional[str] = Field(default=None, max_length=50)


class ConvenioSeguimientoCreate(SQLModel):
    codigo: str
    ies_id: int
    periodo_academico: str
    valor: Optional[Decimal] = None
    fecha_inicio_convenio: Optional[date] = None
    fecha_fin_convenio: Optional[date] = None
    fecha_vencimiento_poliza: Optional[date] = None
    supervisor: Optional[str] = None
    apoyo_supervision: Optional[str] = None
    observaciones_generales: Optional[str] = None
    creado_por: Optional[str] = None


class ConvenioSeguimientoUpdate(SQLModel):
    periodo_academico: Optional[str] = None
    estado: Optional[str] = None
    valor: Optional[Decimal] = None
    fecha_inicio_convenio: Optional[date] = None
    fecha_fin_convenio: Optional[date] = None
    fecha_vencimiento_poliza: Optional[date] = None
    supervisor: Optional[str] = None
    apoyo_supervision: Optional[str] = None
    observaciones_generales: Optional[str] = None


class ConvenioPeriodoSeguimiento(SQLModel, table=True):
    """Tabla convenio_periodos_seg_mc (ya existente, esquema sin cambios)."""
    __tablename__ = "convenio_periodos_seg_mc"

    id: Optional[int] = Field(default=None, primary_key=True)
    convenio_id: int = Field(foreign_key="convenios_seg_proceso_mc.id")
    periodo: str = Field(max_length=20)
    orden: int = Field(default=1)
    creado_en: Optional[datetime] = None


class ConvenioPeriodoCreate(SQLModel):
    periodo: str
