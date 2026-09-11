import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import bindparam, text

from ..core.database import engine_analitica
from ..models.reportes_financieros import (
    CargaExcelResponse,
    ConvenioFinanciero,
    FilaCargaExcel,
    PeriodoFinanciero,
    ReporteFinancieroResponse,
    ResumenCargaExcel,
    ResumenFinanciero,
    UltimaActualizacionResponse,
)
from .seguimiento_auth import get_current_user_seguimiento, require_rol

router = APIRouter(prefix="/reportes-financieros", tags=["Reportes Financieros"])

# NOTA: igual que reportes_inversion.py — se autentica con el login de
# Seguimiento (usuarios_seg_proceso_mc), de solo lectura, cualquier rol
# autenticado puede consultarlo, sin restricción de rol específico. La
# EXCEPCIÓN es POST /cargar-excel (más abajo), que sí restringe a
# ADMIN + AF (Apoyo Financiero) con require_rol — es el único endpoint de
# este router que escribe en la base.


def _construir_where(
    ies: Optional[List[str]],
    convenio: Optional[List[str]],
    periodo: Optional[List[str]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Combina los filtros (cada uno es una LISTA — se puede elegir varias
    IES / varios convenios / varios períodos a la vez, combinados con AND
    entre dimensiones y OR dentro de cada una).

    `periodo` es distinto a `ies`/`convenio`: no es una columna directa de
    `convenios_seg_proceso_mc`, así que se resuelve con un EXISTS contra
    `convenio_periodos_seg_mc` (el registro de períodos que ya administra
    Convenios) — un convenio pasa el filtro si tiene AL MENOS uno de los
    períodos elegidos, sin importar si el financiero ya le cargó ejecución
    para ese período o no (mismo criterio "estructural" que ya usa
    `/convenios/{id}/periodos`, que muestra el período igual aunque esté
    vacío). A pedido de Migue, este filtro además acota qué períodos se
    muestran DENTRO de cada convenio (ver `periodo` en
    `/convenios/{id}/periodos`) y qué datos se suman en el consolidado (ver
    el `WHERE` que se agrega a la subconsulta de agregación en
    `resumen_financiero`) — reutiliza el mismo bind `periodo_list` que se
    arma acá."""
    clausulas = ["1=1"]
    binds: Dict[str, Any] = {}
    if ies:
        clausulas.append("i.nombre IN :ies_list")
        binds["ies_list"] = tuple(ies)
    if convenio:
        clausulas.append("c.codigo IN :convenio_list")
        binds["convenio_list"] = tuple(convenio)
    if periodo:
        clausulas.append("""EXISTS (
            SELECT 1 FROM convenio_periodos_seg_mc pp
            WHERE pp.convenio_id = c.id AND UPPER(TRIM(pp.periodo)) IN :periodo_list
        )""")
        binds["periodo_list"] = tuple(p.strip().upper() for p in periodo)
    return " AND ".join(clausulas), binds


def _bindparams_expandibles(binds: Dict[str, Any]) -> List[Any]:
    return [bindparam(nombre, expanding=True) for nombre in binds if nombre.endswith("_list")]


def _pct_ejecucion_valor(pagado: Optional[float], cdp: Optional[float]) -> Optional[float]:
    """Replica exacta de la fórmula del excel `= VALOR PAGADO / VALOR DE CDP`
    (columna X). None si no hay CDP todavía (no se puede dividir por 0 ni
    tiene sentido mostrar un % sin base)."""
    if not cdp:
        return None
    return (pagado or 0) / cdp


def _pct_ejecucion_tiempo(fecha_inicio, fecha_fin, hoy: date) -> Optional[float]:
    """% de tiempo transcurrido del convenio (días desde fecha_inicio_convenio
    hasta HOY, sobre el total de días del convenio) — se calcula al vuelo con
    la fecha actual cada vez que se pide el reporte, igual que el "% EJECUCIÓN
    (TIEMPO)" del excel del financiero (que era una fórmula =HOY(), no dato
    guardado). None si faltan las fechas o el rango no tiene sentido (fin <=
    inicio). Se limita a [0, 1] — un convenio que ya venció, o que aún no
    arranca, no debería mostrar un % negativo o mayor a 100%."""
    if not fecha_inicio or not fecha_fin:
        return None
    total_dias = (fecha_fin - fecha_inicio).days
    if total_dias <= 0:
        return None
    transcurridos = (hoy - fecha_inicio).days
    return max(0.0, min(1.0, transcurridos / total_dias))


@router.get(
    "/resumen",
    response_model=ReporteFinancieroResponse,
    summary="KPIs financieros (valor total/ejecutado/proyectado) por convenio, filtrable por IES/convenio",
)
def resumen_financiero(
    ies: Optional[List[str]] = Query(None, description="Una o varias IES (nombre exacto). Omitir = todas."),
    convenio: Optional[List[str]] = Query(None, description="Uno o varios códigos de convenio exactos. Omitir = todos."),
    periodo: Optional[List[str]] = Query(
        None,
        description="Uno o varios períodos exactos (ej. '2026-1'). Omitir = todos los períodos de cada convenio. "
        "Además de filtrar qué convenios aparecen, ACOTA los totales de este resumen (y los de "
        "/convenios/{id}/periodos) a solo esos períodos — no a la vida completa del convenio.",
    ),
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> ReporteFinancieroResponse:
    """
    valor_total = convenios_seg_proceso_mc.valor_inicial (columna renombrada
    por Migue; antes se llamaba `valor`. Confirmado con Migue que ya cubre
    "valor total del contrato", no hace falta pedírselo al financiero. El
    campo de la API/JSON sigue llamándose `valor_total` sin cambios — acá
    solo cambió de dónde se lee en la base, vía `AS valor` en el SELECT).
    valor_ejecutado = SUM(valor_pagado) de convenio_ejecucion_financiera_mc
    para ese convenio (confirmado con Migue: lo que realmente salió de caja).
    valor_proyectado = SUM(valor_proyectado_periodo) — se suma across todos
    los períodos del convenio porque el valor proyectado varía por período,
    no es un número único por convenio (a diferencia de un intento anterior
    que sí lo modelaba así, ya revertido).
    valor_cdp = SUM(valor_cdp) — es la base contra la que se calcula
    pct_ejecucion_valor y valor_no_ejecutado, igual que en el excel del
    financiero (ahí es por período: pagado/CDP; acá se suma el CDP de todos
    los períodos con datos y se compara contra el total pagado).
    valor_pagado_men = SUM(valor_pagado_men) — mismo criterio de agregación
    que valor_ejecutado.

    Si se pasa `periodo`, las 4 sumas de arriba (y por lo tanto
    valor_no_ejecutado/pct_ejecucion_valor) se calculan SOLO con las filas de
    convenio_ejecucion_financiera_mc de esos períodos — no con la vida
    completa del convenio — a pedido de Migue (el filtro de período "acota").
    valor_total, adiciones_recursos y pct_ejecucion_tiempo NO cambian con
    este filtro: son atributos del CONVENIO (el valor del contrato, sus
    adiciones, sus fechas), no del período.
    """
    where_sql, binds = _construir_where(ies, convenio, periodo)

    # El filtro de período también restringe QUÉ FILAS se agregan en la
    # subconsulta `e` (no solo qué convenios pasan el WHERE de afuera) —
    # reutiliza el mismo bind `periodo_list` que ya arma `_construir_where`
    # para el EXISTS de convenio_periodos_seg_mc.
    periodo_where_agregacion = ""
    if periodo:
        periodo_where_agregacion = "WHERE UPPER(TRIM(periodo)) IN :periodo_list"

    with engine_analitica.connect() as conn:
        stmt = text(f"""
            SELECT c.id AS convenio_id, c.codigo, i.nombre AS ies_nombre, i.sigla AS ies_sigla,
                   c.periodo_academico, c.estado, c.valor_inicial AS valor, c.adiciones_recursos,
                   c.fecha_inicio_convenio, c.fecha_fin_convenio,
                   COALESCE(e.valor_ejecutado, 0) AS valor_ejecutado,
                   COALESCE(e.valor_proyectado, 0) AS valor_proyectado,
                   COALESCE(e.valor_cdp, 0) AS valor_cdp,
                   COALESCE(e.valor_pagado_men, 0) AS valor_pagado_men
            FROM convenios_seg_proceso_mc c
            JOIN ies_seg_proceso_mc i ON c.ies_id = i.id
            LEFT JOIN (
                SELECT convenio_id,
                       SUM(valor_pagado) AS valor_ejecutado,
                       SUM(valor_proyectado_periodo) AS valor_proyectado,
                       SUM(valor_cdp) AS valor_cdp,
                       SUM(valor_pagado_men) AS valor_pagado_men
                FROM convenio_ejecucion_financiera_mc
                {periodo_where_agregacion}
                GROUP BY convenio_id
            ) e ON e.convenio_id = c.id
            WHERE {where_sql}
            ORDER BY c.codigo
        """)
        stmt = stmt.bindparams(*_bindparams_expandibles(binds))
        filas = conn.execute(stmt, binds).mappings().all()

        # Opciones "facetadas": las opciones de IES/Convenio/Período dependen
        # de las OTRAS 2 dimensiones activas (a pedido de Migue) — si ya
        # eligió una IES, el dropdown de Convenio solo debe ofrecer los
        # convenios de esa IES, y así con las 3 combinaciones. Cada lista se
        # calcula con el filtro de las otras 2 dimensiones únicamente (nunca
        # con la propia: si ya elegiste 2 IES, esas 2 tienen que seguir
        # apareciendo como opción, no desaparecer del propio dropdown).
        where_ies, binds_ies = _construir_where(None, convenio, periodo)
        stmt_ies = text(f"""
            SELECT DISTINCT i.nombre
            FROM ies_seg_proceso_mc i
            JOIN convenios_seg_proceso_mc c ON c.ies_id = i.id
            WHERE {where_ies}
            ORDER BY i.nombre ASC
        """)
        stmt_ies = stmt_ies.bindparams(*_bindparams_expandibles(binds_ies))
        opciones_ies = [r["nombre"] for r in conn.execute(stmt_ies, binds_ies).mappings().all()]

        where_convenio, binds_convenio = _construir_where(ies, None, periodo)
        stmt_convenio = text(f"""
            SELECT DISTINCT c.codigo
            FROM convenios_seg_proceso_mc c
            JOIN ies_seg_proceso_mc i ON c.ies_id = i.id
            WHERE {where_convenio}
            ORDER BY c.codigo ASC
        """)
        stmt_convenio = stmt_convenio.bindparams(*_bindparams_expandibles(binds_convenio))
        opciones_convenio = [r["codigo"] for r in conn.execute(stmt_convenio, binds_convenio).mappings().all()]

        where_periodo, binds_periodo = _construir_where(ies, convenio, None)
        stmt_periodo = text(f"""
            SELECT DISTINCT p.periodo
            FROM convenio_periodos_seg_mc p
            JOIN convenios_seg_proceso_mc c ON c.id = p.convenio_id
            JOIN ies_seg_proceso_mc i ON c.ies_id = i.id
            WHERE {where_periodo}
            ORDER BY p.periodo ASC
        """)
        stmt_periodo = stmt_periodo.bindparams(*_bindparams_expandibles(binds_periodo))
        opciones_periodo = [r["periodo"] for r in conn.execute(stmt_periodo, binds_periodo).mappings().all()]

    hoy = date.today()
    convenios: List[ConvenioFinanciero] = []
    for f in filas:
        valor_total = float(f["valor"] or 0)
        valor_ejecutado = float(f["valor_ejecutado"] or 0)
        valor_proyectado = float(f["valor_proyectado"] or 0)
        valor_cdp = float(f["valor_cdp"] or 0)
        valor_pagado_men = float(f["valor_pagado_men"] or 0)
        convenios.append(
            ConvenioFinanciero(
                convenio_id=f["convenio_id"],
                codigo=f["codigo"],
                ies_nombre=f["ies_nombre"],
                ies_sigla=f["ies_sigla"],
                periodo_academico=f["periodo_academico"],
                estado=f["estado"],
                valor_total=valor_total,
                adiciones_recursos=float(f["adiciones_recursos"] or 0),
                valor_cdp=valor_cdp,
                valor_ejecutado=valor_ejecutado,
                valor_proyectado=valor_proyectado,
                valor_pagado_men=valor_pagado_men,
                valor_no_ejecutado=valor_cdp - valor_ejecutado,
                pct_ejecucion_valor=_pct_ejecucion_valor(valor_ejecutado, valor_cdp),
                pct_ejecucion_tiempo=_pct_ejecucion_tiempo(f["fecha_inicio_convenio"], f["fecha_fin_convenio"], hoy),
            )
        )

    total_valor = sum(c.valor_total for c in convenios)
    total_cdp = sum(c.valor_cdp for c in convenios)
    total_ejecutado = sum(c.valor_ejecutado for c in convenios)
    total_proyectado = sum(c.valor_proyectado for c in convenios)
    total_pagado_men = sum(c.valor_pagado_men for c in convenios)

    resumen = ResumenFinanciero(
        valor_total=total_valor,
        valor_cdp=total_cdp,
        valor_ejecutado=total_ejecutado,
        valor_proyectado=total_proyectado,
        valor_pagado_men=total_pagado_men,
        valor_no_ejecutado=total_cdp - total_ejecutado,
        pct_ejecucion_valor=_pct_ejecucion_valor(total_ejecutado, total_cdp),
        convenios=len(convenios),
    )

    return ReporteFinancieroResponse(
        resumen=resumen,
        convenios=convenios,
        opciones_ies=opciones_ies,
        opciones_convenio=opciones_convenio,
        opciones_periodo=opciones_periodo,
    )


@router.get(
    "/convenios/{convenio_id}/periodos",
    response_model=List[PeriodoFinanciero],
    summary="Detalle de ejecución financiera de un convenio, por período",
)
def periodos_financieros(
    convenio_id: int,
    periodo: Optional[List[str]] = Query(
        None,
        description="Mismo filtro de período que /resumen — si se pasa, solo trae los períodos de este convenio "
        "que coincidan (en vez de todos). Se pasa para que esta llamada quede consistente con lo que ya "
        "filtró /resumen.",
    ),
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> List[PeriodoFinanciero]:
    binds: Dict[str, Any] = {"cid": convenio_id}
    clausula_periodo = ""
    if periodo:
        clausula_periodo = "AND UPPER(TRIM(p.periodo)) IN :periodo_list"
        binds["periodo_list"] = tuple(x.strip().upper() for x in periodo)

    with engine_analitica.connect() as conn:
        existe = conn.execute(text("SELECT id FROM convenios_seg_proceso_mc WHERE id=:cid"), {"cid": convenio_id}).fetchone()
        if not existe:
            raise HTTPException(status_code=404, detail="Convenio no encontrado")

        # LEFT JOIN normalizado en mayúsculas/espacios (mismo criterio que
        # _agregar_periodo_convenio en seguimiento_convenios.py) — así un
        # período que ya existe en Seguimiento pero al que el financiero
        # todavía no le ha mandado datos aparece igual, con los campos de
        # ejecución en NULL, en vez de desaparecer de la lista.
        stmt = text(f"""
            SELECT p.periodo, e.numero_rp, e.numero_cdp, e.valor_cdp,
                   e.estudiantes_postulados, e.estudiantes_conciliados, e.valor_conciliado,
                   e.valor_pagado_matricula, e.valor_pagado_complementarios, e.valor_pagado_ajuste,
                   e.valor_pagado, e.valor_pagado_men, e.valor_proyectado_periodo, e.observaciones
            FROM convenio_periodos_seg_mc p
            LEFT JOIN convenio_ejecucion_financiera_mc e
                ON e.convenio_id = p.convenio_id
                AND UPPER(TRIM(e.periodo)) = UPPER(TRIM(p.periodo))
            WHERE p.convenio_id = :cid {clausula_periodo}
            ORDER BY p.orden, p.id
        """)
        if periodo:
            stmt = stmt.bindparams(bindparam("periodo_list", expanding=True))
        filas = conn.execute(stmt, binds).mappings().all()

    def _f(v):
        return float(v) if v is not None else None

    def _i(v):
        return int(v) if v is not None else None

    periodos = []
    for f in filas:
        valor_cdp = _f(f["valor_cdp"])
        valor_pagado = _f(f["valor_pagado"])
        # Fórmulas exactas del excel del financiero (columnas W y X, leídas
        # directo del archivo): VALOR NO EJECUTADO = VALOR DE CDP - VALOR
        # PAGADO, % EJECUCIÓN (VALOR) = VALOR PAGADO / VALOR DE CDP. Ninguna
        # de las dos usa el valor total del contrato ni el valor proyectado.
        valor_no_ejecutado = (valor_cdp - (valor_pagado or 0)) if valor_cdp is not None else None
        periodos.append(
            PeriodoFinanciero(
                periodo=f["periodo"],
                numero_rp=str(f["numero_rp"]) if f["numero_rp"] is not None else None,
                numero_cdp=str(f["numero_cdp"]) if f["numero_cdp"] is not None else None,
                valor_cdp=valor_cdp,
                estudiantes_postulados=_i(f["estudiantes_postulados"]),
                estudiantes_conciliados=_i(f["estudiantes_conciliados"]),
                valor_conciliado=_f(f["valor_conciliado"]),
                valor_pagado_matricula=_f(f["valor_pagado_matricula"]),
                valor_pagado_complementarios=_f(f["valor_pagado_complementarios"]),
                valor_pagado_ajuste=_f(f["valor_pagado_ajuste"]),
                valor_pagado=valor_pagado,
                valor_pagado_men=_f(f["valor_pagado_men"]),
                valor_proyectado_periodo=_f(f["valor_proyectado_periodo"]),
                valor_no_ejecutado=valor_no_ejecutado,
                pct_ejecucion_valor=_pct_ejecucion_valor(valor_pagado, valor_cdp),
                observaciones=f["observaciones"] if f["observaciones"] not in (None, "") else None,
            )
        )
    return periodos


# =============================================================================
# Carga del excel de ejecución financiera ("MC_Financiera") — antes esto era
# un proceso manual (scripts/generar_sql_ejecucion_financiera.py: el
# financiero mandaba el excel por correo, alguien lo corría a mano y
# revisaba el SQL generado antes de pegarlo en un cliente MySQL). A pedido
# de Migue, se vuelve un botón dentro del aplicativo (solo ADMIN y AF), con
# 2 validaciones que el script manual no podía hacer por no tener acceso a
# la base real desde donde se escribió: que el convenio_id exista, y que el
# período ya esté creado para ese convenio (Administración > Convenios).
# =============================================================================

# Placeholders de texto que trae el excel en columnas que deberían ser
# numéricas ("Pendiente", "Esp. Conci. MEN") — se vuelven None en vez de
# fallar al convertir a número. Mismo criterio que el script manual.
_PLACEHOLDERS_NULOS = {"pendiente", "esp. conci. men", "esp conci men", ""}

# Columnas sin las cuales ni siquiera vale la pena intentar leer el archivo
# (si faltan, probablemente no es el excel correcto). El resto de columnas,
# si faltan, simplemente producen ese campo en None fila por fila — permite
# que el formato evolucione un poco sin romper la carga.
_COLUMNAS_REQUERIDAS = ["convenio_id", "PERIODO", "VALOR DE CDP", "VALOR PAGADO"]

_MAX_BYTES_EXCEL = 15 * 1024 * 1024  # 15 MB
_MAX_FILAS_EXCEL = 5000


def _limpiar_numero(valor: Any) -> Optional[float]:
    """Misma regla que limpiar_numero() en
    scripts/generar_sql_ejecucion_financiera.py — se copia acá (en vez de
    importarla) porque ese script vive fuera del paquete `api` y no se
    instala como dependencia de la API. None si el valor es un placeholder
    de texto; el número tal cual si ya es int/float; si es texto con
    formato de moneda (ej. "$ 526.567.802"), lo limpia a float."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        texto = valor.strip()
        if texto.lower() in _PLACEHOLDERS_NULOS:
            return None
        limpio = re.sub(r"[^\d,.-]", "", texto)
        limpio = limpio.replace(".", "").replace(",", ".") if "," in limpio else limpio.replace(".", "")
        try:
            return float(Decimal(limpio))
        except (InvalidOperation, ValueError):
            return None
    return None


def _limpiar_entero(valor: Any) -> Optional[int]:
    numero = _limpiar_numero(valor)
    return int(numero) if numero is not None else None


def _limpiar_texto(valor: Any) -> Optional[str]:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _normalizar(texto: Optional[str]) -> str:
    """Mismo criterio de comparación case/trim-insensitive que ya usa
    /convenios/{id}/periodos (UPPER(TRIM(...)))."""
    return (texto or "").strip().upper()


@router.post(
    "/cargar-excel",
    response_model=CargaExcelResponse,
    summary="Cargar el excel de ejecución financiera del financiero (previsualizar o aplicar)",
)
async def cargar_excel_financiero(
    archivo: UploadFile = File(..., description="Excel 'MC_Financiera' (una fila por convenio + período)"),
    confirmar: bool = Form(False, description="false = solo valida y previsualiza; true = aplica los cambios"),
    _: Dict[str, Any] = Depends(require_rol("ADMIN", "AF")),
) -> CargaExcelResponse:
    """
    Se llama 2 veces desde el frontend con el MISMO archivo: primero con
    confirmar=false (solo valida, no escribe nada — para mostrar la
    previsualización fila por fila) y, si el usuario confirma, otra vez con
    confirmar=true (recién ahí hace los INSERT/UPDATE, en una sola
    transacción).

    Por fila se valida: que 'convenio_id' exista en convenios_seg_proceso_mc,
    y que 'PERIODO' ya esté creado para ese convenio en
    convenio_periodos_seg_mc (si no, error — no se crea el período
    automáticamente, así se evita saltarse el orden que ya definió
    Administración > Convenios). Además, si el código/IES del excel no
    coincide con los reales de ese convenio_id, o si 'ADICIONES DE RECURSOS'
    trae valores distintos entre filas del mismo convenio, o si el mismo
    convenio+período se repite dentro del propio archivo, se marca como
    advertencia (se aplica igual, pero vale la pena que el financiero lo
    revise).

    Columnas del excel que NO se guardan (fórmulas de Excel recalculables o
    ya administradas en otro lado — ver
    sql/migraciones/2026-09_ejecucion_financiera_convenios.sql):
    "FECHA DE INICIO"/"FECHA FINALIZACIÓN" (las administra Convenios),
    "FECHAS HOY"/"% EJECUCIÓN (TIEMPO)" (se recalcula al vuelo con la fecha
    de hoy), "VALOR TOTAL DEL CONTRATO" (ya es `valor` en
    convenios_seg_proceso_mc, lo administra Convenios), "VALOR NO EJECUTADO"
    y "% EJECUCIÓN (VALOR)" (se recalculan a partir de valor_cdp/valor_pagado).
    """
    contenido = await archivo.read()
    if len(contenido) > _MAX_BYTES_EXCEL:
        raise HTTPException(status_code=400, detail="El archivo supera el tamaño máximo permitido (15 MB).")

    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True, read_only=True)
        ws = wb.active
        filas_iter = ws.iter_rows()
        primera_fila = next(filas_iter)
    except StopIteration:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo — ¿es un .xlsx válido?")

    encabezados = [str(c.value).strip() if c.value is not None else None for c in primera_fila]
    idx = {h: i for i, h in enumerate(encabezados) if h}

    faltantes = [c for c in _COLUMNAS_REQUERIDAS if c not in idx]
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo no tiene el formato esperado — faltan las columnas: {', '.join(faltantes)}.",
        )

    def col(fila: Any, nombre: str) -> Any:
        i = idx.get(nombre)
        if i is None or i >= len(fila):
            return None
        return fila[i].value

    filas_crudas = []
    numero_fila = 1
    for fila in filas_iter:
        numero_fila += 1
        if all(c.value is None for c in fila):
            continue
        filas_crudas.append((numero_fila, fila))

    if not filas_crudas:
        raise HTTPException(status_code=400, detail="El archivo no tiene filas de datos (solo el encabezado).")
    if len(filas_crudas) > _MAX_FILAS_EXCEL:
        raise HTTPException(status_code=400, detail=f"El archivo tiene demasiadas filas (máximo {_MAX_FILAS_EXCEL}).")

    datos_filas = []
    convenio_ids_presentes = set()
    for numero_fila, fila in filas_crudas:
        convenio_id = _limpiar_entero(col(fila, "convenio_id"))
        datos_filas.append({
            "numero_fila": numero_fila,
            "convenio_id": convenio_id,
            "codigo_excel": _limpiar_texto(col(fila, "codigo")),
            "ies_excel": _limpiar_texto(col(fila, "ies")),
            "periodo": _limpiar_texto(col(fila, "PERIODO")),
            "numero_rp": _limpiar_texto(col(fila, "№ RP")),
            "numero_cdp": _limpiar_texto(col(fila, "№ CDP")),
            "valor_cdp": _limpiar_numero(col(fila, "VALOR DE CDP")),
            "estudiantes_postulados": _limpiar_entero(col(fila, "ESTUDIENTES POSTULADOS")),
            "estudiantes_conciliados": _limpiar_entero(col(fila, "ESTUDIANTES CONCILIADOS")),
            "valor_conciliado": _limpiar_numero(col(fila, "VALOR CONCILIADO")),
            "valor_pagado_matricula": _limpiar_numero(col(fila, "MATRICULA")),
            "valor_pagado_complementarios": _limpiar_numero(col(fila, "COMPLEMENTARIOS")),
            "valor_pagado_ajuste": _limpiar_numero(col(fila, "AJUSTES 1,5")),
            "valor_pagado": _limpiar_numero(col(fila, "VALOR PAGADO")),
            # 2 columnas nuevas a pedido de Migue — igual que el resto de
            # columnas "opcionales" de este parser, si el excel todavía no
            # las trae simplemente quedan en None fila por fila (no rompen
            # la carga ni están en _COLUMNAS_REQUERIDAS).
            "valor_pagado_men": _limpiar_numero(col(fila, "VALOR PAGADO MEN")),
            "observaciones": _limpiar_texto(col(fila, "OBSERVACIONES")),
            "valor_proyectado_periodo": _limpiar_numero(col(fila, "VALOR PROYECTADO")),
            "adiciones_recursos": _limpiar_numero(col(fila, "ADICIONES DE RECURSOS")),
        })
        if convenio_id is not None:
            convenio_ids_presentes.add(convenio_id)

    convenios_info: Dict[int, Dict[str, Any]] = {}
    periodos_validos: Dict[int, set] = {}
    # (convenio_id, período normalizado) que YA tienen ejecución financiera
    # cargada — se usa para decidir `accion` ("crear" vs "actualizar") en
    # cada fila, calculado contra el estado de la BD ANTES de esta carga (no
    # cambia entre la llamada de previsualización y la de confirmar, para
    # que se vea lo mismo en las 2).
    ejecucion_existente: set = set()

    with engine_analitica.connect() as conn:
        if convenio_ids_presentes:
            stmt_c = text("""
                SELECT c.id, c.codigo, i.nombre AS ies_nombre, i.sigla AS ies_sigla
                FROM convenios_seg_proceso_mc c
                JOIN ies_seg_proceso_mc i ON c.ies_id = i.id
                WHERE c.id IN :ids
            """).bindparams(bindparam("ids", expanding=True))
            for r in conn.execute(stmt_c, {"ids": tuple(convenio_ids_presentes)}).mappings().all():
                convenios_info[r["id"]] = dict(r)

            stmt_p = text("""
                SELECT convenio_id, periodo FROM convenio_periodos_seg_mc WHERE convenio_id IN :ids
            """).bindparams(bindparam("ids", expanding=True))
            for r in conn.execute(stmt_p, {"ids": tuple(convenio_ids_presentes)}).mappings().all():
                periodos_validos.setdefault(r["convenio_id"], set()).add(_normalizar(r["periodo"]))

            stmt_e = text("""
                SELECT convenio_id, periodo FROM convenio_ejecucion_financiera_mc WHERE convenio_id IN :ids
            """).bindparams(bindparam("ids", expanding=True))
            for r in conn.execute(stmt_e, {"ids": tuple(convenio_ids_presentes)}).mappings().all():
                ejecucion_existente.add((r["convenio_id"], _normalizar(r["periodo"])))

        resultados: List[FilaCargaExcel] = []
        filas_para_aplicar = []
        adiciones_por_convenio: Dict[int, Tuple[float, int]] = {}
        vistos_convenio_periodo: Dict[Tuple[int, str], int] = {}

        for d in datos_filas:
            mensajes: List[str] = []
            estado = "ok"
            convenio_id = d["convenio_id"]
            periodo = d["periodo"]
            info = convenios_info.get(convenio_id) if convenio_id is not None else None

            if convenio_id is None:
                estado = "error"
                mensajes.append("Falta 'convenio_id'.")
            elif info is None:
                estado = "error"
                mensajes.append(f"No existe ningún convenio con id={convenio_id}.")

            if not periodo:
                estado = "error"
                mensajes.append("Falta 'PERIODO'.")
            elif info is not None and _normalizar(periodo) not in periodos_validos.get(convenio_id, set()):
                estado = "error"
                mensajes.append(
                    f"El período '{periodo}' no existe para este convenio — créalo primero en "
                    "Administración > Convenios."
                )

            if info is not None:
                if d["codigo_excel"] and _normalizar(d["codigo_excel"]) != _normalizar(info["codigo"]):
                    estado = "advertencia" if estado == "ok" else estado
                    mensajes.append(
                        f"El código del excel ('{d['codigo_excel']}') no coincide con el código real de este "
                        f"convenio_id ('{info['codigo']}') — revisa que sea el convenio correcto."
                    )
                if d["ies_excel"] and _normalizar(d["ies_excel"]) not in (
                    _normalizar(info["ies_nombre"]), _normalizar(info["ies_sigla"] or "")
                ):
                    estado = "advertencia" if estado == "ok" else estado
                    mensajes.append(
                        f"La IES del excel ('{d['ies_excel']}') no coincide con la IES real de este convenio "
                        f"('{info['ies_nombre']}')."
                    )

            if estado != "error" and convenio_id is not None and periodo:
                clave = (convenio_id, _normalizar(periodo))
                if clave in vistos_convenio_periodo:
                    estado = "advertencia" if estado == "ok" else estado
                    mensajes.append(
                        f"Este convenio+período también aparece en la fila {vistos_convenio_periodo[clave]} de "
                        "este mismo archivo — se aplicó el valor de la última fila leída."
                    )
                vistos_convenio_periodo[clave] = d["numero_fila"]

            if estado != "error" and d["adiciones_recursos"] is not None and convenio_id is not None:
                previo = adiciones_por_convenio.get(convenio_id)
                if previo is not None and previo[0] != d["adiciones_recursos"]:
                    estado = "advertencia" if estado == "ok" else estado
                    mensajes.append(
                        f"'Adiciones de recursos' no coincide con el valor visto en la fila {previo[1]} de este "
                        "convenio — se usó el de esta fila (la última leída)."
                    )
                adiciones_por_convenio[convenio_id] = (d["adiciones_recursos"], d["numero_fila"])

            if estado != "error":
                filas_para_aplicar.append(d)

            accion = None
            if estado != "error" and convenio_id is not None and periodo:
                accion = "actualizar" if (convenio_id, _normalizar(periodo)) in ejecucion_existente else "crear"

            resultados.append(FilaCargaExcel(
                fila_excel=d["numero_fila"],
                convenio_id=convenio_id,
                codigo=(info["codigo"] if info else d["codigo_excel"]),
                periodo=periodo,
                estado=estado,
                accion=accion,
                mensajes=mensajes or ["Todo en orden."],
            ))

        convenios_afectados = len({d["convenio_id"] for d in filas_para_aplicar if d["convenio_id"] is not None})

        if confirmar and filas_para_aplicar:
            # De-duplicar por (convenio_id, período normalizado) — si el
            # mismo archivo trae 2 veces la misma combinación (ya avisado
            # como advertencia arriba), se aplica solo la última fila leída.
            por_clave: Dict[Tuple[int, str], Dict[str, Any]] = {}
            for d in filas_para_aplicar:
                por_clave[(d["convenio_id"], _normalizar(d["periodo"]))] = d

            stmt_upsert = text("""
                INSERT INTO convenio_ejecucion_financiera_mc
                    (convenio_id, periodo, numero_rp, numero_cdp, valor_cdp,
                     estudiantes_postulados, estudiantes_conciliados, valor_conciliado,
                     valor_pagado_matricula, valor_pagado_complementarios, valor_pagado_ajuste,
                     valor_pagado, valor_pagado_men, valor_proyectado_periodo, observaciones, actualizado_en)
                VALUES
                    (:convenio_id, :periodo, :numero_rp, :numero_cdp, :valor_cdp,
                     :estudiantes_postulados, :estudiantes_conciliados, :valor_conciliado,
                     :valor_pagado_matricula, :valor_pagado_complementarios, :valor_pagado_ajuste,
                     :valor_pagado, :valor_pagado_men, :valor_proyectado_periodo, :observaciones, NOW())
                ON DUPLICATE KEY UPDATE
                    numero_rp = VALUES(numero_rp), numero_cdp = VALUES(numero_cdp), valor_cdp = VALUES(valor_cdp),
                    estudiantes_postulados = VALUES(estudiantes_postulados),
                    estudiantes_conciliados = VALUES(estudiantes_conciliados),
                    valor_conciliado = VALUES(valor_conciliado),
                    valor_pagado_matricula = VALUES(valor_pagado_matricula),
                    valor_pagado_complementarios = VALUES(valor_pagado_complementarios),
                    valor_pagado_ajuste = VALUES(valor_pagado_ajuste),
                    valor_pagado = VALUES(valor_pagado),
                    valor_pagado_men = VALUES(valor_pagado_men),
                    valor_proyectado_periodo = VALUES(valor_proyectado_periodo),
                    observaciones = VALUES(observaciones),
                    actualizado_en = NOW()
            """)
            for d in por_clave.values():
                conn.execute(stmt_upsert, {k: d[k] for k in (
                    "convenio_id", "periodo", "numero_rp", "numero_cdp", "valor_cdp",
                    "estudiantes_postulados", "estudiantes_conciliados", "valor_conciliado",
                    "valor_pagado_matricula", "valor_pagado_complementarios", "valor_pagado_ajuste",
                    "valor_pagado", "valor_pagado_men", "valor_proyectado_periodo", "observaciones",
                )})

            for convenio_id, (monto, _fila) in adiciones_por_convenio.items():
                conn.execute(
                    text("UPDATE convenios_seg_proceso_mc SET adiciones_recursos=:monto WHERE id=:id"),
                    {"monto": monto, "id": convenio_id},
                )

            conn.commit()

    resumen = ResumenCargaExcel(
        confirmado=confirmar,
        filas_leidas=len(datos_filas),
        filas_aplicadas=len(filas_para_aplicar) if confirmar else 0,
        filas_con_advertencia=sum(1 for r in resultados if r.estado == "advertencia"),
        filas_con_error=sum(1 for r in resultados if r.estado == "error"),
        convenios_afectados=convenios_afectados,
        # Mismo criterio que filas_aplicadas: cuenta filas del excel (antes
        # de de-duplicar convenio+período repetido dentro del propio
        # archivo), no filas netas escritas en la BD.
        filas_nuevas=sum(1 for r in resultados if r.accion == "crear"),
        filas_actualizadas=sum(1 for r in resultados if r.accion == "actualizar"),
    )
    return CargaExcelResponse(resumen=resumen, filas=resultados)


@router.get(
    "/ultima-actualizacion",
    response_model=UltimaActualizacionResponse,
    summary="Fecha de la última carga de datos del módulo financiero",
)
def ultima_actualizacion_financiero(
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> UltimaActualizacionResponse:
    """A pedido de Migue: una tarjeta con la fecha de actualización de cada
    uno de los 3 módulos del selector de apps. Acá, la fecha de la carga de
    excel más reciente (ver `actualizado_en` — se pone explícitamente en
    cada INSERT/UPDATE del upsert de /cargar-excel, así que refleja tanto
    la primera carga como cualquier re-carga posterior)."""
    with engine_analitica.connect() as conn:
        fila = conn.execute(text("SELECT MAX(actualizado_en) AS fecha FROM convenio_ejecucion_financiera_mc")).mappings().fetchone()
    return UltimaActualizacionResponse(fecha=fila["fecha"] if fila else None)