from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import text

class InformacionPersonal(SQLModel, table=True):
    __tablename__ = "informacion_personal"
    docconvfondo: str = Field(primary_key=True)
    id_usuario: str
    documento: str
    convocatoria: str
    fondo_sapiencia: str
    nombre_completo: str | None = None
    genero: str | None = None
    lgtbi: str | None = None
    fecha_nacimiento: datetime | None = None
    telefono: str | None = None
    celular: str | None = None
    celular_alternativo: str | None = None
    correo: str | None = None
    correo_alternativo: str | None = None
    estrato_residencia_legalizacion: str | None = None
    estrato_residencia_actual: str | None = None
    direccion_residencia_legalizacion: str | None = None
    direccion_residencia_actual: str | None = None
    comuna_residencia_legalizacion: str | None = None
    comuna_residencia_actual: str | None = None
    municipio_residencia_legalizacion: str | None = None
    municipio_residencia_actual: str | None = None
    barrio_residencia_legalizacion: str | None = None
    barrio_residencia_actual: str | None = None
    victima_conflicto: str | None = None
    hecho_victimizante: str | None = None
    situacion_discapacidad: str | None = None
    tipo_discapacidad: str | None = None
    puntaje_sisben: str | None = None
    pertenece_etnia: str | None = None
    tipo_etnia: str | None = None
    fecha_actualizacion: datetime | None = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )
    responsable_actualizacion: str | None = None


class InformacionPersonalUpdate(SQLModel):
    # docconvfondo no se actualiza por body; va en el path
    id_usuario: str | None = None
    documento: str | None = None
    convocatoria: str | None = None
    fondo_sapiencia: str | None = None
    nombre_completo: str | None = None
    genero: str | None = None
    lgtbi: str | None = None
    fecha_nacimiento: datetime | None = None
    telefono: str | None = None
    celular: str | None = None
    celular_alternativo: str | None = None
    correo: str | None = None
    correo_alternativo: str | None = None
    estrato_residencia_legalizacion: str | None = None
    estrato_residencia_actual: str | None = None
    direccion_residencia_legalizacion: str | None = None
    direccion_residencia_actual: str | None = None
    comuna_residencia_legalizacion: str | None = None
    comuna_residencia_actual: str | None = None
    municipio_residencia_legalizacion: str | None = None
    municipio_residencia_actual: str | None = None
    barrio_residencia_legalizacion: str | None = None
    barrio_residencia_actual: str | None = None
    victima_conflicto: str | None = None
    hecho_victimizante: str | None = None
    situacion_discapacidad: str | None = None
    tipo_discapacidad: str | None = None
    puntaje_sisben: str | None = None
    pertenece_etnia: str | None = None
    tipo_etnia: str | None = None
    responsable_actualizacion: str | None = None
