from typing import Optional

from sqlmodel import Field, SQLModel


class IESPregPosg(SQLModel, table=True):
    __tablename__ = "ies_preg_posg"

    id: Optional[int] = Field(default=None, primary_key=True)
    id_ies: str = Field(max_length=20)
    nombre_ies: Optional[str] = Field(default=None, max_length=200)
    estado: Optional[str] = Field(default=None, max_length=20)
    sector: Optional[str] = Field(default=None, max_length=20)
    conteo_ies: Optional[str] = Field(default=None, max_length=100)


class IESPregPosgCreate(SQLModel):
    id_ies: str
    nombre_ies: Optional[str] = None
    estado: Optional[str] = None
    sector: Optional[str] = None
    conteo_ies: Optional[str] = None


class IESPregPosgUpdate(SQLModel):
    # Todos opcionales para permitir actualizaciones parciales
    id_ies: Optional[str] = None
    nombre_ies: Optional[str] = None
    estado: Optional[str] = None
    sector: Optional[str] = None
    conteo_ies: Optional[str] = None