from datetime import date
from typing import Any, Dict, List, Literal, Optional

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


# ---------------------------------------------------------------------------
# POST /matricula-cero/tablero/cargar-mc-final
#
# La previsualización (confirmar=false) NO lista fila por fila como
# Financiero — con archivos de hasta ~24 mil filas (IES grandes como ITM)
# eso sería inmanejable. En cambio: un resumen con conteos, y el DETALLE
# solo de las filas que necesitan revisión antes de confirmar. Categorías
# de "problema" (confirmadas con Migue):
#   - duplicado_en_archivo: el mismo documento+período aparece 2+ veces
#     DENTRO de este mismo excel (típicamente un error de digitación).
#   - conflicto_ies: ese documento+período YA existe en mc_final pero bajo
#     OTRA IES (ej. un estudiante evaluado por 2 IES distintas) — no se
#     sobrescribe solo, Migue decide cuál IES es la correcta.
#   - docperiodo_ambiguo: ese documento+período ya tiene 2+ filas
#     duplicadas históricas en mc_final (de antes de este flujo) — se
#     reporta para revisión manual, no se toca.
#   - renueva_sin_historial: fila RENUEVA cuyo período anterior (que el
#     propio excel ya trae referenciado) no hizo match en mc_final — se
#     sube igual, pero con semestre_ingreso/giros en el placeholder "NO
#     ENCONTRADO" en vez de un valor real (confirmado con Migue: sí debe
#     aparecer como problema a revisar, no solo un aviso menor).
#   - invalida: fila sin DOCUMENTO, no se puede procesar.
#   - excluida_manual: fila con SUBIR_A_BD=NO — no es un problema, es una
#     exclusión intencional, pero se reporta igual para que quede visible.
# ---------------------------------------------------------------------------

TipoProblemaMcFinal = Literal[
    "duplicado_en_archivo",
    "conflicto_ies",
    "docperiodo_ambiguo",
    "renueva_sin_historial",
    "invalida",
    "excluida_manual",
]


class FilaProblemaMcFinal(BaseModel):
    fila_excel: int
    documento: Optional[str] = None
    ies: Optional[str] = None
    tipo: TipoProblemaMcFinal
    mensaje: str


class ResumenCargaMcFinal(BaseModel):
    confirmado: bool
    periodo: str
    filas_leidas: int
    filas_excluidas_manual: int
    filas_invalidas: int
    # De las filas sin ningún problema bloqueante:
    filas_correctas: int
    filas_nuevas: int
    filas_actualizan: int
    # Categorías de "para revisar" (ver docstring arriba) — cada una cuenta
    # también en el detalle de `problemas` de CargaMcFinalResponse.
    filas_duplicadas_en_archivo: int
    filas_conflicto_ies: int
    filas_docperiodo_ambiguo: int
    filas_renueva_sin_historial: int
    # Solo tiene sentido cuando confirmado=true: cuántas filas realmente se
    # escribieron (insertadas + actualizadas). En la previsualización queda
    # en 0 (no se escribió nada todavía).
    filas_aplicadas: int


class CargaMcFinalResponse(BaseModel):
    resumen: ResumenCargaMcFinal
    # Detalle SOLO de las filas con problema — nunca de las miles de filas
    # correctas (por diseño, para que la previsualización sea manejable con
    # archivos de decenas de miles de filas).
    problemas: List[FilaProblemaMcFinal]
