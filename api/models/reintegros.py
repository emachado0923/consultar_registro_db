from datetime import date, datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import text
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel


class Reintegros(SQLModel, table=True):
    __tablename__ = "reintegros"
    
    id: int | None = Field(default=None, primary_key=True)
    beneficiario: str = Field(nullable=False, max_length=100)
    ies: str = Field(nullable=False, max_length=100)
    documento: str = Field(nullable=False, max_length=20)
    monto_girado: Decimal = Field(nullable=False, max_digits=15, decimal_places=2)
    monto_reintegro: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)
    fecha_reporte: date = Field(nullable=False)
    estado_correo: str | None = Field(default=None, max_length=50)
    certificado: str | None = Field(default=None, max_length=50)
    estado_fiducia: str | None = Field(default=None, max_length=50)
    fecha_efectuado: date | None = Field(default=None)
    fecha_registro: datetime | None = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )


class ReintegrosCreate(SQLModel):
    beneficiario: str
    ies: str
    documento: str
    monto_girado: float
    monto_reintegro: Optional[float] | None = None
    fecha_reporte: date
    estado_correo: str | None = None
    certificado: str | None = None
    estado_fiducia: str | None = None
    fecha_efectuado: date | None = None


class ReintegrosUpdate(SQLModel):
    beneficiario: str | None = None
    ies: str | None = None
    documento: str | None = None
    monto_girado: float | None = None
    monto_reintegro: Optional[float] | None = None
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
    monto_girado: float
    monto_reintegro: Optional[float] = None
    fecha_reporte: date
    estado_correo: Optional[str] = None
    certificado: Optional[str] = None
    estado_fiducia: Optional[str] = None
    fecha_efectuado: Optional[date] = None
    fecha_registro: Optional[datetime] = None

    class Config:
        from_attributes = True