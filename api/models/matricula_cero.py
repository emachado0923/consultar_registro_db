from datetime import date
from typing import Any, Dict, Optional

from pydantic import BaseModel


class InfoPersonalMCResponse(BaseModel):
    """Respuesta de /matricula-cero/tablero/info-personal — equivalente a
    tablero_mc.py::_cargar_info_personal, para el período más reciente
    diligenciado por el documento."""
    encontrado: bool
    periodo_label: Optional[str] = None
    datos: Optional[Dict[str, Any]] = None


class UltimaActualizacionTableroResponse(BaseModel):
    """Ver GET /matricula-cero/tablero/ultima-actualizacion — a pedido de
    Migue, la tarjeta de "fecha de actualización" para el Tablero histórico
    (la mitad de Consulta+Tablero que SÍ necesita una, a diferencia de
    /consulta y /tablero/info-personal: esas 2 consultan
    convocatoria_sapiencia en vivo, sin ningún paso de carga/importación de
    por medio — confirmado con Migue).

    `fecha` = MAX(fecha_cargue) de analitica_fondos.mc_final (columna
    nueva, ver migración 2026-09_fecha_cargue_mc_final.sql) — es un DATE,
    no un datetime con hora, porque así se cargó el dato: por lotes
    (períodos viejos sin fecha porque no se sabe cuándo se cargaron
    originalmente, períodos nuevos con la fecha del día en que se subió
    ese lote). None solo si NINGUNA fila de mc_final tiene fecha_cargue
    todavía (o la tabla está vacía)."""
    fecha: Optional[date] = None
