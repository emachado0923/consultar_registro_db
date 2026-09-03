from typing import List, Optional

from pydantic import BaseModel


class ConvenioDetalleOut(BaseModel):
    id: int
    codigo: str
    ies_nombre: str
    ies_sigla: Optional[str] = None
    periodo_academico: str
    estado: str
    valor: Optional[float] = None
    valor_proyectado: Optional[float] = None
    fecha_inicio_convenio: Optional[str] = None
    fecha_fin_convenio: Optional[str] = None
    fecha_limite_liquidacion_voluntaria: Optional[str] = None
    fecha_limite_liquidacion_unilateral: Optional[str] = None
    fecha_limite_liquidacion_judicial: Optional[str] = None
    fecha_vencimiento_poliza: Optional[str] = None
    fecha_firma_director_general: Optional[str] = None
    supervisor: Optional[str] = None
    apoyo_supervision: Optional[str] = None
    observaciones_generales: Optional[str] = None
    creado_por: Optional[str] = None
    nivel_alerta: Optional[str] = None  # AVISO | URGENTE | CRÍTICO | None
    motivos_alerta: List[str] = []
