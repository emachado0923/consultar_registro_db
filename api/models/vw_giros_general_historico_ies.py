from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime, date

class VwGirosGeneralHistoricoIes(SQLModel, table=True):
    __tablename__ = "vw_giros_general_historico_ies"
    
    # Columnas principales (ajusta los tipos según necesites)
    documento: str = Field(primary_key=True, max_length=100)
    solicitud: Optional[str] = Field(default=None, max_length=100)
    solicitud_nuevo_fiduciaria: Optional[str] = Field(default=None, max_length=100)
    convocatoria: Optional[str] = Field(default=None, max_length=100)
    convocatoria_numero: Optional[str] = Field(default=None, max_length=100)
    encargo_fiduciario: Optional[str] = Field(default=None, max_length=100)
    orden_pago_sostenimiento: Optional[str] = Field(default=None, max_length=100)
    orden_pago_matricula: Optional[str] = Field(default=None, max_length=100)
    periodo: Optional[str] = Field(default=None, max_length=100)
    estado: Optional[str] = Field(default=None, max_length=100)
    tipo_documento: Optional[str] = Field(default=None, max_length=100)
    documento_actual: Optional[str] = Field(default=None, max_length=100)
    documento_anterior: Optional[str] = Field(default=None, max_length=100)
    genero: Optional[str] = Field(default=None, max_length=100)
    fecha_nacimiento: Optional[date] = None
    nombre: Optional[str] = Field(default=None, max_length=200)
    primerApellido: Optional[str] = Field(default=None, max_length=100)
    segundoApellido: Optional[str] = Field(default=None, max_length=100)
    primerNombre: Optional[str] = Field(default=None, max_length=100)
    segundoNombre: Optional[str] = Field(default=None, max_length=100)
    ies: Optional[str] = Field(default=None, max_length=200)
    programa: Optional[str] = Field(default=None, max_length=200)
    modalidad: Optional[str] = Field(default=None, max_length=100)
    semestre_cursar: Optional[str] = Field(default=None, max_length=50)
    giros_solicitados: Optional[int] = None
    giros_realizados: Optional[int] = None
    debito: Optional[str] = Field(default=None, max_length=100)
    consignacion_sostenimiento: Optional[str] = Field(default=None, max_length=100)
    valor_debito: Optional[float] = None
    valor_debito_real: Optional[str] = Field(default=None, max_length=100)
    valor_liquidacion_matricula: Optional[float] = None
    valor_pagar_matricula: Optional[float] = None
    valor_pagar_sostenimiento: Optional[float] = None
    valor_girar: Optional[float] = None
    fecha_registro: Optional[datetime] = None
    departamento_nacimiento: Optional[str] = Field(default=None, max_length=100)
    municipio_nacimiento: Optional[str] = Field(default=None, max_length=100)
    departamento_residencia: Optional[str] = Field(default=None, max_length=100)
    municipio_residencia: Optional[str] = Field(default=None, max_length=100)
    barrio: Optional[str] = Field(default=None, max_length=100)
    comuna: Optional[str] = Field(default=None, max_length=100)
    estrato: Optional[str] = Field(default=None, max_length=10)
    direccion: Optional[str] = Field(default=None)
    telefono: Optional[str] = Field(default=None, max_length=50)
    celular: Optional[str] = Field(default=None, max_length=50)
    correo: Optional[str] = Field(default=None, max_length=200)
    correo_alterno: Optional[str] = Field(default=None, max_length=200)
    observacion: Optional[str] = Field(default=None)
    corte_aprobado: Optional[str] = Field(default=None, max_length=100)
    fondo: Optional[str] = Field(default=None, max_length=200)
    periodo_academico: Optional[str] = Field(default=None, max_length=100)
    id_fondo: Optional[int] = None