from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel


class InformacionCambioPensum(SQLModel, table=True):
    __tablename__ = "informacion_cambio_pensum"
    
    docconvfondo: str = Field(primary_key=True, max_length=30)
    documento: str = Field(max_length=20)
    convocatoria: str = Field(max_length=20)
    fondo: str = Field(max_length=50)
    ies_actual: Optional[str] = Field(default=None, max_length=150)
    programa_actual: Optional[str] = Field(default=None, max_length=150)
    numero_semestres_pensum_anterior: Optional[int] = Field(default=None)
    numero_semestres_pensum_actual: Optional[int] = Field(default=None)
    numero_creditos_pensum_anterior: Optional[int] = Field(default=None)
    numero_creditos_pensum_actual: Optional[int] = Field(default=None)
    periodo_efectivo_cambio: Optional[str] = Field(default=None, max_length=6)
    radicado_pqrs_cambio: Optional[str] = Field(default=None, max_length=50)
    fecha_actualizacion: datetime = Field(
        default=None,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )
    responsable_actualizacion: Optional[str] = Field(default=None, max_length=100)


class InformacionCambioPensumCreate(SQLModel):
    docconvfondo: str
    documento: str
    convocatoria: str
    fondo: str
    ies_actual: Optional[str] = None
    programa_actual: Optional[str] = None
    numero_semestres_pensum_anterior: Optional[int] = None
    numero_semestres_pensum_actual: Optional[int] = None
    numero_creditos_pensum_anterior: Optional[int] = None
    numero_creditos_pensum_actual: Optional[int] = None
    periodo_efectivo_cambio: Optional[str] = None
    radicado_pqrs_cambio: Optional[str] = None
    responsable_actualizacion: Optional[str] = None


class InformacionCambioPensumUpdate(SQLModel):
    documento: Optional[str] = None
    convocatoria: Optional[str] = None
    fondo: Optional[str] = None
    ies_actual: Optional[str] = None
    programa_actual: Optional[str] = None
    numero_semestres_pensum_anterior: Optional[int] = None
    numero_semestres_pensum_actual: Optional[int] = None
    numero_creditos_pensum_anterior: Optional[int] = None
    numero_creditos_pensum_actual: Optional[int] = None
    periodo_efectivo_cambio: Optional[str] = None
    radicado_pqrs_cambio: Optional[str] = None
    responsable_actualizacion: Optional[str] = None


class InformacionCambioPensumResponse(BaseModel):
    docconvfondo: str
    documento: str
    convocatoria: str
    fondo: str
    ies_actual: Optional[str] = None
    programa_actual: Optional[str] = None
    numero_semestres_pensum_anterior: Optional[int] = None
    numero_semestres_pensum_actual: Optional[int] = None
    numero_creditos_pensum_anterior: Optional[int] = None
    numero_creditos_pensum_actual: Optional[int] = None
    periodo_efectivo_cambio: Optional[str] = None
    radicado_pqrs_cambio: Optional[str] = None
    fecha_actualizacion: Optional[datetime] = None
    responsable_actualizacion: Optional[str] = None

    class Config:
        from_attributes = True