from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from ..core.database import engine_analitica, engine_convocatoria
from ..core.matricula_cero_helpers import calcular_periodo_label
from ..models.consulta import ConsultaResponse
from ..models.matricula_cero import InfoPersonalMCResponse
from .auth import get_current_user

router = APIRouter(prefix="/matricula-cero", tags=["Matrícula Cero"])


@router.get(
    "/consulta",
    response_model=ConsultaResponse,
    summary="Consultar formulario de Matrícula Cero (vista vigente 2026-2)",
)
def consulta_formulario_2026_2(
    documento: str = Query(..., min_length=6, max_length=15),
    _: Dict[str, Any] = Depends(get_current_user),
) -> ConsultaResponse:
    """
    Endpoint NUEVO y separado de /consulta/formulario-mc (que se deja intacto,
    apuntando a la vista 2025-2). Este consulta la vista vigente
    vw_matricula_cero_2026_2 — equivalente a
    app/database/db_operations.py::MatriculaCeroOperations.get_by_documento
    del portal Streamlit.
    """
    q = text("""
        SELECT *
        FROM vw_matricula_cero_2026_2
        WHERE documento = :documento
        ORDER BY fecha_registro DESC
    """)
    with engine_convocatoria.connect() as conn:
        rows = conn.execute(q, {"documento": documento}).mappings().all()

    results: List[Dict[str, Any]] = [dict(r) for r in rows]
    return ConsultaResponse(count=len(results), results=results)


@router.get(
    "/tablero/info-personal",
    response_model=InfoPersonalMCResponse,
    summary="Información personal del formulario más reciente (Tablero Matrícula Cero)",
)
def tablero_info_personal(
    documento: str = Query(..., min_length=6, max_length=15),
    _: Dict[str, Any] = Depends(get_current_user),
) -> InfoPersonalMCResponse:
    """
    Equivalente a tablero_mc.py::_cargar_info_personal: consulta directamente
    convocatoria_sapiencia.matricula_cero (con sus tablas de referencia/catálogo)
    filtrando el ÚLTIMO período registrado para el documento — sin depender de
    ninguna vista. A diferencia del original (que arma la consulta con
    f-strings), aquí el documento va parametrizado para evitar inyección SQL.
    """
    q = text("""
        SELECT mc.*,
               a.nombre  AS tipo_documento,
               b.nombre  AS pais_nacimiento,
               d.nombre  AS departamento_nacimiento,
               c.nombre  AS municipio_nacimiento,
               e.nombre  AS sexo,
               f.nombre  AS orientacion_sexual,
               g.nombre  AS identidad_genero,
               i.nombre  AS afiliacion_salud,
               j.nombre  AS tipo_vivienda,
               k.nombre  AS actividad_realiza,
               m.nombre  AS estrato,
               n.nombre  AS pais_residencia_ubg,
               o.nombre  AS departamento_ubicacion,
               p.nombre  AS municipio_ubicacion,
               q.nombre  AS barrio,
               r.nombre  AS comuna,
               w.nombre  AS nivel_academico,
               yy.nombre AS beneficio_sapiencia,
               z.nombre  AS ies_adscritas,
               zz.nombre AS programa_admitido,
               aa.nombre AS semestre_academico,
               'Completo' AS estado_formulario
        FROM convocatoria_sapiencia.matricula_cero mc
        LEFT JOIN convocatoria_sapiencia.vlf_tipo_documento      a  ON a.id  = mc.tipo_documento
        LEFT JOIN convocatoria_sapiencia.pais                    b  ON b.id  = mc.pais_nacimiento
        LEFT JOIN convocatoria_sapiencia.departamento            d  ON d.id  = mc.departamento_residencia
        LEFT JOIN convocatoria_sapiencia.municipio               c  ON c.id  = mc.municipio_residencia
        LEFT JOIN convocatoria_sapiencia.odes_expectativas_sexo  e  ON e.id  = mc.sexo
        LEFT JOIN convocatoria_sapiencia.estudiantes_orientacion_sexual f ON f.id = mc.orientacion_sexual
        LEFT JOIN convocatoria_sapiencia.estudiantes_identidad_genero   g ON g.id = mc.identidad_genero
        LEFT JOIN convocatoria_sapiencia.tipo_regimen_salud      i  ON i.id  = mc.afiliacion_salud
        LEFT JOIN convocatoria_sapiencia.talento_especializado_tipo_vivienda j ON j.id = mc.tipo_vivienda
        LEFT JOIN convocatoria_sapiencia.actividad_matricula_cero k  ON k.id  = mc.actividad_realiza
        LEFT JOIN convocatoria_sapiencia.vlf_estrato             m  ON m.id  = mc.estrato
        LEFT JOIN convocatoria_sapiencia.pais                    n  ON n.id  = mc.pais_residencia_ubg
        LEFT JOIN convocatoria_sapiencia.departamento            o  ON o.id  = mc.departamento_ubg
        LEFT JOIN convocatoria_sapiencia.municipio               p  ON p.id  = mc.municipio_residencia_ubg
        LEFT JOIN convocatoria_sapiencia.barrio                  q  ON q.id  = mc.barrio
        LEFT JOIN convocatoria_sapiencia.comuna_caracterizacion  r  ON r.id  = mc.comuna
        LEFT JOIN convocatoria_sapiencia.nivel_academico_matricula_cero w ON w.id = mc.nivel_academico
        LEFT JOIN convocatoria_sapiencia.matriculacero_beneficio_sapiencia yy ON yy.id = mc.beneficio_sapiencia
        LEFT JOIN convocatoria_sapiencia.ies_acoso_sexual        z  ON z.id  = mc.ies_adscritas
        LEFT JOIN convocatoria_sapiencia.ies_matricula_cero_actual zz ON zz.id = mc.programa_admitido
        LEFT JOIN convocatoria_sapiencia.semestre_matricula_cero aa ON aa.id = mc.semestre_academico
        WHERE mc.documento = :documento
          AND mc.periodo = (
              SELECT MAX(mc2.periodo)
              FROM convocatoria_sapiencia.matricula_cero mc2
              WHERE mc2.documento = :documento
          )
        LIMIT 1
    """)
    with engine_convocatoria.connect() as conn:
        row = conn.execute(q, {"documento": documento}).mappings().fetchone()

    if not row:
        return InfoPersonalMCResponse(encontrado=False)

    datos = dict(row)
    periodo_label = calcular_periodo_label(datos.get("periodo"))
    return InfoPersonalMCResponse(encontrado=True, periodo_label=periodo_label, datos=datos)


@router.get(
    "/tablero/giros",
    response_model=ConsultaResponse,
    summary="Historial de giros/seguimiento académico por período (Tablero Matrícula Cero)",
)
def tablero_giros(
    documento: str = Query(..., min_length=6, max_length=15),
    solo_proyecto: bool = Query(
        True,
        description="Si es True (por defecto), solo incluye períodos desde 2023-2 en adelante "
                    "(el proyecto actual). Si es False, incluye todo el histórico.",
    ),
    _: Dict[str, Any] = Depends(get_current_user),
) -> ConsultaResponse:
    """
    Equivalente a tablero_mc.py::_cargar_analitica + el filtro
    df_analitica_filtrado (columna 'periodo' es texto tipo 'AAAA-S' en esta
    tabla — distinto del código entero de matricula_cero — se compara igual
    que en el original, lexicográficamente).
    """
    q = text("""
        SELECT *
        FROM analitica_fondos.mc_final
        WHERE documento = :documento
        ORDER BY periodo ASC
    """)
    with engine_analitica.connect() as conn:
        rows = conn.execute(q, {"documento": documento}).mappings().all()

    results: List[Dict[str, Any]] = [dict(r) for r in rows]
    if solo_proyecto:
        results = [r for r in results if str(r.get("periodo", "")) >= "2023-2"]

    return ConsultaResponse(count=len(results), results=results)
