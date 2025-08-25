from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlmodel import Field, SQLModel


class InformacionProgramasAcademicos(SQLModel, table=True):
    __tablename__ = "informacion_programas_academicos"

    docconvfondo: str = Field(primary_key=True)
    documento: str
    convocatoria: str
    fondo: str
    ies_legalizacion: Optional[str] = None
    ies_actual: Optional[str] = None
    programa_legalizacion: Optional[str] = None
    programa_actual: Optional[str] = None
    numero_semestres_programa: Optional[int] = None
    numero_total_creditos_programa: Optional[int] = None
    es_cuatrimestral: str = Field(default=".")
    cambio_afecta_numero_giros_proyectados_inicialmente: Optional[str] = None
    cuantos_giros_reducidos_proyectados: Optional[int] = None
    periodo_efectivo_cambio: Optional[str] = None
    radicado_pqrs_cambio: Optional[str] = None
    fecha_actualizacion: datetime | None = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )
    responsable_actualizacion: Optional[str] = None


class InformacionProgramasAcademicosUpdate(SQLModel):
    documento: Optional[str] = None
    convocatoria: Optional[str] = None
    fondo: Optional[str] = None
    ies_legalizacion: Optional[str] = None
    ies_actual: Optional[str] = None
    programa_legalizacion: Optional[str] = None
    programa_actual: Optional[str] = None
    numero_semestres_programa: Optional[int] = None
    numero_total_creditos_programa: Optional[int] = None
    es_cuatrimestral: Optional[str] = None
    cambio_afecta_numero_giros_proyectados_inicialmente: Optional[str] = None
    cuantos_giros_reducidos_proyectados: Optional[int] = None
    periodo_efectivo_cambio: Optional[str] = None
    radicado_pqrs_cambio: Optional[str] = None
    responsable_actualizacion: Optional[str] = None
