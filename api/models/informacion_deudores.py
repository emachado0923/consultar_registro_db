from typing import Optional

from sqlmodel import Field, SQLModel


class InformacionDeudoresBase(SQLModel):
    docconvfondo: str = Field(max_length=50)
    id_usuario: str = Field(max_length=20)
    documento: str = Field(max_length=20)
    convocatoria: str = Field(max_length=20)
    fondo_sapiencia: str = Field(max_length=50)
    tipo_documento_deudor: Optional[str] = Field(default=None, max_length=50)
    documento_deudor: Optional[str] = Field(default=None, max_length=26)
    nombre_deudor: Optional[str] = Field(default=None, max_length=150)
    parentesco_deudor: Optional[str] = Field(default=None, max_length=50)
    telefono_deudor: Optional[str] = Field(default=None, max_length=20)
    celular_deudor: Optional[str] = Field(default=None, max_length=20)
    correo_deudor: Optional[str] = Field(default=None, max_length=150)
    direccion_residencia_deudor: Optional[str] = Field(default=None, max_length=200)
    departamento_residencia_deudor: Optional[str] = Field(
        default=None, max_length=100
    )
    municipio_residencia_deudor: Optional[str] = Field(default=None, max_length=100)
    tiempo_residencia_deudor: Optional[str] = Field(default=None, max_length=100)
    comuna_residencia_deudor: Optional[str] = Field(default=None, max_length=50)


class InformacionDeudores(InformacionDeudoresBase, table=True):
    __tablename__ = "informacion_deudores"
    idconvfondo: str = Field(primary_key=True, max_length=50)


class InformacionDeudoresCreate(InformacionDeudoresBase):
    idconvfondo: str = Field(max_length=50)


class InformacionDeudoresUpdate(SQLModel):
    tipo_documento_deudor: Optional[str] = None
    documento_deudor: Optional[str] = None
    nombre_deudor: Optional[str] = None
    parentesco_deudor: Optional[str] = None
    telefono_deudor: Optional[str] = None
    celular_deudor: Optional[str] = None
    correo_deudor: Optional[str] = None
    direccion_residencia_deudor: Optional[str] = None
    departamento_residencia_deudor: Optional[str] = None
    municipio_residencia_deudor: Optional[str] = None
    tiempo_residencia_deudor: Optional[str] = None
    comuna_residencia_deudor: Optional[str] = None
