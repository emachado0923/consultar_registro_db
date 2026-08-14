from typing import Optional

from sqlmodel import Field, SQLModel


class ActividadBaseSeguimiento(SQLModel, table=True):
    """
    Tabla actividades_base_seg_mc (ya existente, esquema sin cambios).

    NOTA: la columna 'aplica_a' sigue existiendo en la BD pero ya NO se usa
    (se revirtió el filtro automático por tipo de IES a favor del botón manual
    "No aplica" por actividad, ver ActividadConvenioSeguimiento.no_aplica).
    Se deja aquí solo para que el modelo refleje el esquema real; los
    endpoints nuevos no la exponen para creación/edición.
    """
    __tablename__ = "actividades_base_seg_mc"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    descripcion: Optional[str] = None
    tipo: str = Field(max_length=20)  # ejecucion | liquidacion | cierre
    subcategoria: str = Field(max_length=150)
    subcategoria_orden: int = Field(default=0)
    orden: int
    es_relevante: Optional[int] = Field(default=0)
    tiene_fecha_limite: Optional[int] = Field(default=1)
    aplica_a: Optional[str] = Field(default="Todas", max_length=20)  # deprecado, no usar
    peso_relativo: Optional[float] = Field(default=1.00)


class ActividadBaseCreate(SQLModel):
    # 'tipo' ya llega como parámetro de ruta en POST /seguimiento/catalogo/{tipo}
    # (create_actividad_catalogo usa exclusivamente ese valor, nunca data.tipo),
    # así que el body real que manda el frontend no lo incluye. Antes 'tipo'
    # era obligatorio acá, lo que hacía que ESE POST fallara siempre con 422
    # "tipo: Field required" — se deja opcional porque nunca se lee del body.
    tipo: Optional[str] = None
    nombre: str
    subcategoria: str
    subcategoria_orden: int = 1
    orden: int
    es_relevante: bool = True
    tiene_fecha_limite: bool = False


class ActividadBaseUpdate(SQLModel):
    nombre: Optional[str] = None
    subcategoria: Optional[str] = None
    subcategoria_orden: Optional[int] = None
    orden: Optional[int] = None
    es_relevante: Optional[bool] = None
    tiene_fecha_limite: Optional[bool] = None
