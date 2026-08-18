from datetime import datetime
from typing import Optional
 
from pydantic import BaseModel
from sqlmodel import Field, SQLModel
 
 
class UsuarioSeguimiento(SQLModel, table=True):
    """
    Tabla usuarios_seg_proceso_mc (ya existente, esquema sin cambios).
    rol: ENUM('ADMIN','DIRECTORA','LMC','AST','AD','AF','AJ') en la BD.
    """
    __tablename__ = "usuarios_seg_proceso_mc"
 
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=100)
    usuario: str = Field(max_length=50, sa_column_kwargs={"unique": True})
    password_hash: str = Field(max_length=255)
    rol: str = Field(max_length=20)
    activo: Optional[int] = Field(default=1)
    primer_login: Optional[int] = Field(default=1)
    creado_en: Optional[datetime] = Field(default=None)
 
 
class UsuarioSeguimientoPublic(BaseModel):
    """Igual que UsuarioSeguimiento pero sin password_hash, para no exponerlo en respuestas."""
    id: int
    nombre: str
    usuario: str
    rol: str
    activo: Optional[int] = 1
    primer_login: Optional[int] = 1
    creado_en: Optional[datetime] = None
 
 
class UsuarioSeguimientoCreate(BaseModel):
    nombre: str
    usuario: str
    password: str
    rol: str  # ADMIN | DIRECTORA | LMC | AST | AD | AF | AJ
 
 
class UsuarioSeguimientoEstadoUpdate(BaseModel):
    activo: int  # 0 o 1
 
 
class UsuarioSeguimientoPasswordUpdate(BaseModel):
    """Reseteo de contraseña hecho por un ADMIN (no el propio usuario) —
    distinto del cambio de contraseña de primer login (ese lo hace el
    usuario sobre sí mismo, ver /seguimiento/auth/cambiar-password)."""
    password: str
