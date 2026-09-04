from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import bindparam, text

from ..core.database import engine_analitica
from ..models.reportes_financieros import (
    ConvenioFinanciero,
    PeriodoFinanciero,
    ReporteFinancieroResponse,
    ResumenFinanciero,
)
from .seguimiento_auth import get_current_user_seguimiento

router = APIRouter(prefix="/reportes-financieros", tags=["Reportes Financieros"])

# NOTA: igual que reportes_inversion.py — se autentica con el login de
# Seguimiento (usuarios_seg_proceso_mc), de solo lectura, cualquier rol
# autenticado puede consultarlo, sin restricción de rol específico.


def _construir_where(ies: Optional[List[str]], convenio: Optional[List[str]]) -> Tuple[str, Dict[str, Any]]:
    """Combina los 2 filtros (cada uno es una LISTA — se puede elegir varias
    IES / varios convenios a la vez, combinados con AND entre dimensiones y
    OR dentro de cada una)."""
    clausulas = ["1=1"]
    binds: Dict[str, Any] = {}
    if ies:
        clausulas.append("i.nombre IN :ies_list")
        binds["ies_list"] = tuple(ies)
    if convenio:
        clausulas.append("c.codigo IN :convenio_list")
        binds["convenio_list"] = tuple(convenio)
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
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> ReporteFinancieroResponse:
    """
    valor_total = convenios_seg_proceso_mc.valor (confirmado con Migue que ya
    cubre "valor total del contrato", no hace falta pedírselo al financiero).
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
    """
    where_sql, binds = _construir_where(ies, convenio)

    with engine_analitica.connect() as conn:
        stmt = text(f"""
            SELECT c.id AS convenio_id, c.codigo, i.nombre AS ies_nombre, i.sigla AS ies_sigla,
                   c.periodo_academico, c.estado, c.valor, c.adiciones_recursos,
                   c.fecha_inicio_convenio, c.fecha_fin_convenio,
                   COALESCE(e.valor_ejecutado, 0) AS valor_ejecutado,
                   COALESCE(e.valor_proyectado, 0) AS valor_proyectado,
                   COALESCE(e.valor_cdp, 0) AS valor_cdp
            FROM convenios_seg_proceso_mc c
            JOIN ies_seg_proceso_mc i ON c.ies_id = i.id
            LEFT JOIN (
                SELECT convenio_id,
                       SUM(valor_pagado) AS valor_ejecutado,
                       SUM(valor_proyectado_periodo) AS valor_proyectado,
                       SUM(valor_cdp) AS valor_cdp
                FROM convenio_ejecucion_financiera_mc
                GROUP BY convenio_id
            ) e ON e.convenio_id = c.id
            WHERE {where_sql}
            ORDER BY c.codigo
        """)
        stmt = stmt.bindparams(*_bindparams_expandibles(binds))
        filas = conn.execute(stmt, binds).mappings().all()

        opciones_ies = [
            r["nombre"]
            for r in conn.execute(text("SELECT DISTINCT nombre FROM ies_seg_proceso_mc ORDER BY nombre ASC")).mappings().all()
        ]
        opciones_convenio = [
            r["codigo"]
            for r in conn.execute(text("SELECT codigo FROM convenios_seg_proceso_mc ORDER BY codigo ASC")).mappings().all()
        ]

    hoy = date.today()
    convenios: List[ConvenioFinanciero] = []
    for f in filas:
        valor_total = float(f["valor"] or 0)
        valor_ejecutado = float(f["valor_ejecutado"] or 0)
        valor_proyectado = float(f["valor_proyectado"] or 0)
        valor_cdp = float(f["valor_cdp"] or 0)
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
                valor_no_ejecutado=valor_cdp - valor_ejecutado,
                pct_ejecucion_valor=_pct_ejecucion_valor(valor_ejecutado, valor_cdp),
                pct_ejecucion_tiempo=_pct_ejecucion_tiempo(f["fecha_inicio_convenio"], f["fecha_fin_convenio"], hoy),
            )
        )

    total_valor = sum(c.valor_total for c in convenios)
    total_cdp = sum(c.valor_cdp for c in convenios)
    total_ejecutado = sum(c.valor_ejecutado for c in convenios)
    total_proyectado = sum(c.valor_proyectado for c in convenios)

    resumen = ResumenFinanciero(
        valor_total=total_valor,
        valor_cdp=total_cdp,
        valor_ejecutado=total_ejecutado,
        valor_proyectado=total_proyectado,
        valor_no_ejecutado=total_cdp - total_ejecutado,
        pct_ejecucion_valor=_pct_ejecucion_valor(total_ejecutado, total_cdp),
        convenios=len(convenios),
    )

    return ReporteFinancieroResponse(
        resumen=resumen,
        convenios=convenios,
        opciones_ies=opciones_ies,
        opciones_convenio=opciones_convenio,
    )


@router.get(
    "/convenios/{convenio_id}/periodos",
    response_model=List[PeriodoFinanciero],
    summary="Detalle de ejecución financiera de un convenio, por período",
)
def periodos_financieros(
    convenio_id: int,
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> List[PeriodoFinanciero]:
    with engine_analitica.connect() as conn:
        existe = conn.execute(text("SELECT id FROM convenios_seg_proceso_mc WHERE id=:cid"), {"cid": convenio_id}).fetchone()
        if not existe:
            raise HTTPException(status_code=404, detail="Convenio no encontrado")

        # LEFT JOIN normalizado en mayúsculas/espacios (mismo criterio que
        # _agregar_periodo_convenio en seguimiento_convenios.py) — así un
        # período que ya existe en Seguimiento pero al que el financiero
        # todavía no le ha mandado datos aparece igual, con los campos de
        # ejecución en NULL, en vez de desaparecer de la lista.
        filas = conn.execute(
            text("""
                SELECT p.periodo, e.numero_rp, e.numero_cdp, e.valor_cdp,
                       e.estudiantes_postulados, e.estudiantes_conciliados, e.valor_conciliado,
                       e.valor_pagado_matricula, e.valor_pagado_complementarios, e.valor_pagado_ajuste,
                       e.valor_pagado, e.valor_proyectado_periodo
                FROM convenio_periodos_seg_mc p
                LEFT JOIN convenio_ejecucion_financiera_mc e
                    ON e.convenio_id = p.convenio_id
                    AND UPPER(TRIM(e.periodo)) = UPPER(TRIM(p.periodo))
                WHERE p.convenio_id = :cid
                ORDER BY p.orden, p.id
            """),
            {"cid": convenio_id},
        ).mappings().all()

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
                valor_proyectado_periodo=_f(f["valor_proyectado_periodo"]),
                valor_no_ejecutado=valor_no_ejecutado,
                pct_ejecucion_valor=_pct_ejecucion_valor(valor_pagado, valor_cdp),
            )
        )
    return periodos
