from typing import Any, Dict, List, Optional, Tuple
 
from fastapi import APIRouter, Depends, Query
from sqlalchemy import bindparam, text
 
from ..core.database import engine_analitica
from ..models.reportes_inversion import (
    GrupoInversion,
    ReporteInversionResponse,
    ResumenInversion,
)
from .seguimiento_auth import get_current_user_seguimiento
 
router = APIRouter(prefix="/reportes-inversion", tags=["Reportes de Inversión"])
 
# NOTA: igual que matricula_cero.py, se autentica con el login de
# Seguimiento (usuarios_seg_proceso_mc) — es de solo lectura, cualquier rol
# autenticado puede consultarlo, sin restricción de rol específico.
 
# Confirmado con Migue: una fila de mc_final solo cuenta como beneficio real
# (y por lo tanto su plata como inversión ejecutada) si estado_semestral =
# 'MC' — sin este filtro se estarían sumando/contando filas que no
# corresponden a un beneficio vigente ese período. Aplica tanto a los
# conteos (beneficios/beneficiarios) como a las sumas de dinero por rubro
# (confirmado explícitamente con Migue, no es una suposición).
_ESTADO_MC = "estado_semestral = 'MC'"
 
_SELECT_AGREGADOS = """
    SUM(COALESCE(mat_n, 0))       AS matricula,
    SUM(COALESCE(der_comp_n, 0))  AS complementarios,
    SUM(COALESCE(ajust_n, 0))     AS ajuste,
    COUNT(*)                      AS beneficios,
    COUNT(DISTINCT documento)     AS beneficiarios
"""
 
 
def _anio_de_periodo(periodo: Optional[str]) -> Optional[str]:
    """
    "periodo" en mc_final viene como texto "AAAA-S" (ej: "2023-2") — el año
    se deriva partiendo ese texto (en SQL se usa LEFT(periodo, 4), aquí en
    Python el equivalente para post-procesar la lista de opciones). No hay
    columna de año propia, y esto NO usa la tabla de anclaje de
    matricula_cero_helpers.py (esa es para otra tabla/periodo).
    """
    if not periodo:
        return None
    return str(periodo).split("-")[0].strip() or None
 
 
def _construir_where(
    ies: Optional[List[str]],
    periodo: Optional[List[str]],
    anio: Optional[List[str]],
    excluir: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Combina los 3 filtros (cada uno es ahora una LISTA — se puede elegir
    varias IES / varios años / varios períodos a la vez, combinados con AND
    entre dimensiones y OR dentro de cada una, el comportamiento estándar de
    "IN (...)"). Siempre exige estado_semestral = 'MC'.
 
    `excluir` es la dimensión que esta consulta puntual NO debe filtrar —
    se usa en por_ies (no filtra por ies, para tener siempre el ranking
    completo entre IES) y en por_periodo (no filtra por periodo, para tener
    siempre la tendencia histórica completa).
    """
    clausulas = [_ESTADO_MC]
    binds: Dict[str, Any] = {}
 
    if excluir != "ies" and ies:
        clausulas.append("ies IN :ies_list")
        binds["ies_list"] = tuple(ies)
    if excluir != "periodo" and periodo:
        clausulas.append("periodo IN :periodo_list")
        binds["periodo_list"] = tuple(periodo)
    if excluir != "anio" and anio:
        clausulas.append("LEFT(periodo, 4) IN :anio_list")
        binds["anio_list"] = tuple(anio)
 
    return " AND ".join(clausulas), binds
 
 
def _bindparams_expandibles(binds: Dict[str, Any]) -> List[Any]:
    return [bindparam(nombre, expanding=True) for nombre in binds if nombre.endswith("_list")]
 
 
def _consulta_agregada(conn, where_sql: str, binds: Dict[str, Any]) -> Dict[str, Any]:
    """Una sola fila de agregados (usada para el resumen general, sin GROUP BY)."""
    stmt = text(f"SELECT {_SELECT_AGREGADOS} FROM analitica_fondos.mc_final WHERE {where_sql}")
    stmt = stmt.bindparams(*_bindparams_expandibles(binds))
    return dict(conn.execute(stmt, binds).mappings().one())
 
 
def _consulta_agrupada(conn, columna_agrupacion: str, where_sql: str, binds: Dict[str, Any], orden: str) -> List[Dict[str, Any]]:
    """Filas agregadas agrupadas por IES o por período, ordenadas según `orden`."""
    stmt = text(f"""
        SELECT {columna_agrupacion} AS clave, {_SELECT_AGREGADOS}
        FROM analitica_fondos.mc_final
        WHERE {columna_agrupacion} IS NOT NULL AND {where_sql}
        GROUP BY {columna_agrupacion}
        ORDER BY {orden}
    """)
    stmt = stmt.bindparams(*_bindparams_expandibles(binds))
    return [dict(r) for r in conn.execute(stmt, binds).mappings().all()]
 
 
def _fila_a_grupo(row: Dict[str, Any], clave: str) -> GrupoInversion:
    matricula = float(row["matricula"] or 0)
    complementarios = float(row["complementarios"] or 0)
    ajuste = float(row["ajuste"] or 0)
    return GrupoInversion(
        clave=clave,
        matricula=matricula,
        complementarios=complementarios,
        ajuste=ajuste,
        total=matricula + complementarios + ajuste,
        beneficios=int(row["beneficios"] or 0),
        beneficiarios=int(row["beneficiarios"] or 0),
    )
 
 
@router.get(
    "/resumen",
    response_model=ReporteInversionResponse,
    summary="KPIs de inversión ejecutada y beneficios/beneficiarios, por IES/período/año",
)
def resumen_inversion(
    ies: Optional[List[str]] = Query(None, description="Una o varias IES (nombre exacto, tal como está en mc_final.ies). Omitir = todas."),
    periodo: Optional[List[str]] = Query(None, description='Uno o varios períodos exactos, ej: "2026-1". Omitir = todos.'),
    anio: Optional[List[str]] = Query(None, description='Uno o varios años, ej: "2026" (se compara contra LEFT(periodo, 4)). Omitir = todos.'),
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> ReporteInversionResponse:
    """
    Fuente: analitica_fondos.mc_final (confirmado con Migue como la fuente
    autoritativa de inversión ejecutada). Ver docstring de
    api/models/reportes_inversion.py para el detalle de qué es cada rubro,
    y _ESTADO_MC arriba para el filtro de estado_semestral = 'MC' (aplica
    tanto a conteos como a sumas de dinero, confirmado con Migue).
    """
    where_resumen, binds_resumen = _construir_where(ies, periodo, anio)
    where_ies, binds_ies = _construir_where(ies, periodo, anio, excluir="ies")
    where_periodo, binds_periodo = _construir_where(ies, periodo, anio, excluir="periodo")
 
    with engine_analitica.connect() as conn:
        fila_resumen = _consulta_agregada(conn, where_resumen, binds_resumen)
        filas_ies = _consulta_agrupada(conn, "ies", where_ies, binds_ies, orden="(matricula + complementarios + ajuste) DESC")
        filas_periodo = _consulta_agrupada(conn, "periodo", where_periodo, binds_periodo, orden="clave ASC")
 
        opciones_ies = [
            r["ies"]
            for r in conn.execute(
                text(f"SELECT DISTINCT ies FROM analitica_fondos.mc_final WHERE ies IS NOT NULL AND {_ESTADO_MC} ORDER BY ies ASC")
            ).mappings().all()
        ]
        opciones_periodo = [
            r["periodo"]
            for r in conn.execute(
                text(f"SELECT DISTINCT periodo FROM analitica_fondos.mc_final WHERE periodo IS NOT NULL AND {_ESTADO_MC} ORDER BY periodo ASC")
            ).mappings().all()
        ]
 
    matricula = float(fila_resumen["matricula"] or 0)
    complementarios = float(fila_resumen["complementarios"] or 0)
    ajuste = float(fila_resumen["ajuste"] or 0)
 
    resumen = ResumenInversion(
        matricula=matricula,
        complementarios=complementarios,
        ajuste=ajuste,
        total=matricula + complementarios + ajuste,
        beneficios=int(fila_resumen["beneficios"] or 0),
        beneficiarios=int(fila_resumen["beneficiarios"] or 0),
    )
 
    por_ies: List[GrupoInversion] = [_fila_a_grupo(r, str(r["clave"])) for r in filas_ies]
    por_periodo: List[GrupoInversion] = [_fila_a_grupo(r, str(r["clave"])) for r in filas_periodo]
 
    opciones_anio = sorted({a for a in (_anio_de_periodo(p) for p in opciones_periodo) if a})
 
    return ReporteInversionResponse(
        resumen=resumen,
        por_ies=por_ies,
        por_periodo=por_periodo,
        opciones_ies=opciones_ies,
        opciones_periodo=opciones_periodo,
        opciones_anio=opciones_anio,
    )