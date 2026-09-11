from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel


class ConvenioSeguimiento(SQLModel, table=True):
    """Tabla convenios_seg_proceso_mc — OJO: esta clase NO se usa para
    consultar ni escribir la tabla en ningún endpoint (todo el código real
    usa SQL crudo con `text()`, ver seguimiento_convenios.py); vive acá solo
    como referencia/documentación del esquema real. Por eso, al renombrar
    una columna en la base hace falta actualizar el SQL crudo en los
    routers (no esta clase), pero igual se mantiene actualizada acá para
    que siga sirviendo como referencia fiel.

    `valor_inicial` (antes `valor`, renombrada por Migue directamente en la
    base) — el campo de la API/JSON sigue llamándose `valor` a propósito
    (ver `ConvenioSeguimientoCreate`/`ConvenioSeguimientoUpdate` más abajo,
    y el alias `AS valor` en el SQL de los routers que la leen) — Migue
    decidió no propagar el rename al contrato de la API para no tocar el
    frontend ni arriesgar el módulo de Seguimiento."""
    __tablename__ = "convenios_seg_proceso_mc"

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=50, sa_column_kwargs={"unique": True})
    ies_id: int = Field(foreign_key="ies_seg_proceso_mc.id")
    periodo_academico: str = Field(max_length=10)
    estado: Optional[str] = Field(default="En ejecución", max_length=20)
    valor_inicial: Optional[Decimal] = Field(default=None)
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
    # Se mantiene "valor" a propósito, aunque la columna real ahora se llama
    # `valor_inicial` — es el campo de la API/JSON, y Migue decidió no
    # tocar ese contrato (ver nota en ConvenioSeguimiento arriba). El router
    # traduce este nombre al de la columna real al armar el INSERT.
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
    # Mismo criterio que en ConvenioSeguimientoCreate: se mantiene "valor"
    # como nombre de campo de la API — el router lo traduce a la columna
    # real (`valor_inicial`) antes de armar el UPDATE dinámico.
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
