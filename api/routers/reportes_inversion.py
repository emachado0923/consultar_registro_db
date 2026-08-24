from typing import Any, Dict, List, Optional
 
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
 
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
 
# "periodo" en mc_final viene como texto "AAAA-S" (ej: "2023-2"), a
# diferencia del código entero de convocatoria_sapiencia.matricula_cero —
# el año se deriva partiendo ese texto por el guion, NO con la tabla de
# anclaje de matricula_cero_helpers.py (que es para OTRA tabla/periodo).
def _anio_de_periodo(periodo: Optional[str]) -> Optional[str]:
    if not periodo:
        return None
    return str(periodo).split("-")[0].strip() or None
 
 
# Condición reutilizada en las 3 consultas: cada filtro es opcional (NULL =
# "sin filtrar en esta dimensión"). El de año compara contra el prefijo
# "AAAA-" del texto de periodo en vez de una columna de año propia, porque
# esa columna no existe en mc_final.
_FILTRO_IES = "(:ies IS NULL OR ies = :ies)"
_FILTRO_PERIODO = "(:periodo IS NULL OR periodo = :periodo)"
_FILTRO_ANIO = "(:anio IS NULL OR periodo LIKE CONCAT(:anio, '-%'))"
 
 
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
    ies: Optional[str] = Query(None, description="Nombre exacto de la IES (tal como está en mc_final.ies). Omitir = todas."),
    periodo: Optional[str] = Query(None, description='Período exacto, ej: "2026-1". Omitir = todos.'),
    anio: Optional[str] = Query(None, description='Año, ej: "2026" (se compara contra el prefijo de "periodo"). Omitir = todos.'),
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> ReporteInversionResponse:
    """
    Fuente: analitica_fondos.mc_final (confirmado con Migue como la fuente
    autoritativa de inversión ejecutada). Ver docstring de
    api/models/reportes_inversion.py para el detalle de qué es cada rubro y
    cómo se cuentan beneficios/beneficiarios.
    """
    params = {"ies": ies or None, "periodo": periodo or None, "anio": anio or None}
 
    q_resumen = text(f"""
        SELECT
            SUM(COALESCE(mat_n, 0))       AS matricula,
            SUM(COALESCE(der_comp_n, 0))  AS complementarios,
            SUM(COALESCE(ajust_n, 0))     AS ajuste,
            COUNT(*)                      AS beneficios,
            COUNT(DISTINCT documento)     AS beneficiarios
        FROM analitica_fondos.mc_final
        WHERE {_FILTRO_IES} AND {_FILTRO_PERIODO} AND {_FILTRO_ANIO}
    """)
 
    # por_ies: se agrupa por IES sin aplicar el filtro de IES (para tener
    # siempre el ranking completo), pero sí respeta período/año.
    q_por_ies = text(f"""
        SELECT
            ies AS clave,
            SUM(COALESCE(mat_n, 0))       AS matricula,
            SUM(COALESCE(der_comp_n, 0))  AS complementarios,
            SUM(COALESCE(ajust_n, 0))     AS ajuste,
            COUNT(*)                      AS beneficios,
            COUNT(DISTINCT documento)     AS beneficiarios
        FROM analitica_fondos.mc_final
        WHERE ies IS NOT NULL AND {_FILTRO_PERIODO} AND {_FILTRO_ANIO}
        GROUP BY ies
        ORDER BY (SUM(COALESCE(mat_n, 0)) + SUM(COALESCE(der_comp_n, 0)) + SUM(COALESCE(ajust_n, 0))) DESC
    """)
 
    # por_periodo: se agrupa por período sin aplicar el filtro de período
    # (para tener siempre la tendencia histórica completa), pero sí respeta
    # IES/año.
    q_por_periodo = text(f"""
        SELECT
            periodo AS clave,
            SUM(COALESCE(mat_n, 0))       AS matricula,
            SUM(COALESCE(der_comp_n, 0))  AS complementarios,
            SUM(COALESCE(ajust_n, 0))     AS ajuste,
            COUNT(*)                      AS beneficios,
            COUNT(DISTINCT documento)     AS beneficiarios
        FROM analitica_fondos.mc_final
        WHERE periodo IS NOT NULL AND {_FILTRO_IES} AND {_FILTRO_ANIO}
        GROUP BY periodo
        ORDER BY periodo ASC
    """)
 
    q_opciones_ies = text("SELECT DISTINCT ies FROM analitica_fondos.mc_final WHERE ies IS NOT NULL ORDER BY ies ASC")
    q_opciones_periodo = text("SELECT DISTINCT periodo FROM analitica_fondos.mc_final WHERE periodo IS NOT NULL ORDER BY periodo ASC")
 
    with engine_analitica.connect() as conn:
        fila_resumen = conn.execute(q_resumen, params).mappings().one()
        filas_ies = conn.execute(q_por_ies, params).mappings().all()
        filas_periodo = conn.execute(q_por_periodo, params).mappings().all()
        opciones_ies = [r["ies"] for r in conn.execute(q_opciones_ies).mappings().all()]
        opciones_periodo = [r["periodo"] for r in conn.execute(q_opciones_periodo).mappings().all()]
 
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
 
    # Años derivados de los períodos existentes (no hay columna de año en
    # mc_final), deduplicados y ordenados.
    opciones_anio = sorted({a for a in (_anio_de_periodo(p) for p in opciones_periodo) if a})
 
    return ReporteInversionResponse(
        resumen=resumen,
        por_ies=por_ies,
        por_periodo=por_periodo,
        opciones_ies=opciones_ies,
        opciones_periodo=opciones_periodo,
        opciones_anio=opciones_anio,
    )