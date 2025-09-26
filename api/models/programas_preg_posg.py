from typing import Optional

from sqlmodel import Field, SQLModel


class ProgramasPregPosg(SQLModel, table=True):
    __tablename__ = "programas_preg_posg"

    id: Optional[int] = Field(default=None, primary_key=True)
    id_programa: str = Field(max_length=20)
    id_ies: Optional[str] = Field(default=None, max_length=20)
    estado: Optional[str] = Field(default=None, max_length=100)
    recibe_nuevos: Optional[str] = Field(default=None, max_length=100)
    codigo_snies: Optional[str] = Field(default=None, max_length=100)
    nombre_programa: str = Field(max_length=500)
    tipo_programa: str = Field(max_length=50)
    conteo_programa: str = Field(max_length=100)


class ProgramasPregPosgCreate(SQLModel):
    id_programa: str
    id_ies: Optional[str] = None
    estado: Optional[str] = None
    recibe_nuevos: Optional[str] = None
    codigo_snies: Optional[str] = None
    nombre_programa: str
    tipo_programa: str
    conteo_programa: str


class ProgramasPregPosgUpdate(SQLModel):
    id_programa: Optional[str] = None
    id_ies: Optional[str] = None
    estado: Optional[str] = None
    recibe_nuevos: Optional[str] = None
    codigo_snies: Optional[str] = None
    nombre_programa: Optional[str] = None
    tipo_programa: Optional[str] = None
    conteo_programa: Optional[str] = None