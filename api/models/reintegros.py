from datetime import date, datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel


class Reintegros(SQLModel, table=True):
    __tablename__ = "reintegros"
    
    id: int | None = Field(default=None, primary_key=True)
    beneficiario: str = Field(nullable=False, max_length=100)
    ies: str = Field(nullable=False, max_length=100)
    documento: str = Field(nullable=False, max_length=20)
    monto_girado: int = Field(nullable=False)
    monto_reintegro: int = Field(nullable=False)
    modalidad_reintegro: str | None = Field(default=None, max_length=50)
    fecha_reporte: date = Field(nullable=False)
    estado_correo: str | None = Field(default=None, max_length=50)
    certificado: str | None = Field(default=None, max_length=50)
    estado_fiducia: str | None = Field(default=None, max_length=50)
    fecha_efectuado: date | None = Field(default=None)


class ReintegrosCreate(SQLModel):
    beneficiario: str
    ies: str
    documento: str
    monto_girado: int
    monto_reintegro: int
    modalidad_reintegro: str
    fecha_reporte: date
    estado_correo: str | None = None
    certificado: str | None = None
    estado_fiducia: str | None = None
    fecha_efectuado: date | None = None


class ReintegrosUpdate(SQLModel):
    beneficiario: str | None = None
    ies: str | None = None
    documento: str | None = None
    monto_girado: int | None = None
    monto_reintegro: int | None = None
    modalidad_reintegro: str | None = None
    fecha_reporte: date | None = None
    estado_correo: str | None = None
    certificado: str | None = None
    estado_fiducia: str | None = None
    fecha_efectuado: date | None = None


class ReintegroResponse(BaseModel):
    id: int
    beneficiario: str
    ies: str
    documento: str
    monto_girado: int
    monto_reintegro: int
    modalidad_reintegro: str | None
    fecha_reporte: date
    estado_correo: str | None = None
    certificado: str | None = None
    estado_fiducia: str | None = None
    fecha_efectuado: date | None = None

    class Config:
        from_attributes = True