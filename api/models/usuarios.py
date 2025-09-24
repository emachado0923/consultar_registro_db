from typing import Optional

from sqlmodel import Field, SQLModel


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, sa_column_kwargs={"unique": True})
    password_hash: str = Field(max_length=255)
    sal: str = Field(max_length=32)  # salt
    nombre_completo: Optional[str] = Field(default=None, max_length=100)
    activo: Optional[int] = Field(default=1)
    creado_en: Optional[str] = Field(default=None, max_length=50)


class UsuarioCreate(SQLModel):
    username: str
    password_hash: str
    sal: str
    nombre_completo: Optional[str] = None
    activo: Optional[int] = 1


class UsuarioUpdate(SQLModel):
    # Todos opcionales para poder actualizar parcialmente
    password_hash: Optional[str] = None
    sal: Optional[str] = None
    nombre_completo: Optional[str] = None
    activo: Optional[int] = None
