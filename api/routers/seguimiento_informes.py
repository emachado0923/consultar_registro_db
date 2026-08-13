from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text

from ..core.actividades_seguimiento import calcular_nivel_alerta_convenio
from ..core.database import engine_analitica
from ..core.informes_seguimiento import generar_pdf_informe, get_datos_informe_periodo
from .seguimiento_auth import get_current_user_seguimiento

router = APIRouter(prefix="/seguimiento/informes", tags=["Seguimiento · Informes"])


def _get_convenio_detalle_row(convenio_id: int) -> Dict[str, Any]:
    with engine_analitica.connect() as conn:
        row = conn.execute(
            text("""
                SELECT c.id, c.codigo, i.nombre AS ies_nombre, i.sigla AS ies_sigla,
                       c.periodo_academico, c.estado, c.valor,
                       c.fecha_inicio_convenio, c.fecha_fin_convenio,
                       c.fecha_limite_liquidacion_voluntaria, c.fecha_limite_liquidacion_unilateral,
                       c.fecha_limite_liquidacion_judicial, c.fecha_vencimiento_poliza,
                       c.supervisor, c.apoyo_supervision, c.observaciones_generales,
                       c.creado_por, c.creado_en, c.fecha_firma_director_general
                FROM convenios_seg_proceso_mc c
                JOIN ies_seg_proceso_mc i ON c.ies_id = i.id
                WHERE c.id = :cid
            """),
            {"cid": convenio_id},
        ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Convenio no encontrado")
    return dict(row)


def _get_periodos_convenio(convenio_id: int) -> List[Dict[str, Any]]:
    with engine_analitica.connect() as conn:
        rows = conn.execute(
            text("SELECT id, periodo, orden FROM convenio_periodos_seg_mc WHERE convenio_id=:cid ORDER BY orden, id"),
            {"cid": convenio_id},
        ).mappings().all()
    return [dict(r) for r in rows]


def _armar_contexto(
    det: Dict[str, Any],
    periodos_a_mostrar: List[Dict[str, Any]],
    titulo_informe: str,
    incluir_alerta: bool,
    incluir_fechas: bool,
    incluir_ejecucion: bool,
    incluir_liquidacion: bool,
    incluir_cierre: bool,
    incluir_comentarios: bool,
    usuario_nombre: str,
) -> Dict[str, Any]:
    nivel_alerta, motivos_alerta = calcular_nivel_alerta_convenio(
        engine_analitica,
        det["id"],
        det["fecha_limite_liquidacion_voluntaria"],
        det["fecha_limite_liquidacion_unilateral"],
        det["fecha_limite_liquidacion_judicial"],
        det["fecha_vencimiento_poliza"],
        det["fecha_firma_director_general"],
        det["estado"],
    )

    tipos_incluidos = []
    if incluir_ejecucion:
        tipos_incluidos.append(("ejecucion", "ejecución"))
    if incluir_liquidacion:
        tipos_incluidos.append(("liquidacion", "liquidación"))
    if incluir_cierre:
        tipos_incluidos.append(("cierre", "cierre"))

    periodos_contexto = []
    for p in periodos_a_mostrar:
        datos = get_datos_informe_periodo(engine_analitica, p["id"])
        periodos_contexto.append({
            "label": p["periodo"],
            "tipos": [
                {
                    "etiqueta": etq,
                    "pct_global": datos[tk]["pct_global"],
                    "total": datos[tk]["total"],
                    "subcats": [
                        {"nombre": sc, **info}
                        for sc, info in sorted(datos[tk]["subcats"].items(), key=lambda x: x[1]["sub_orden"])
                    ],
                }
                for tk, etq in tipos_incluidos
            ],
        })

    return {
        "titulo": titulo_informe,
        "codigo": det["codigo"], "ies_nombre": det["ies_nombre"], "sigla": det["ies_sigla"],
        "estado": det["estado"], "periodo_texto": det["periodo_academico"],
        "supervisor": det["supervisor"], "apoyo": det["apoyo_supervision"],
        "valor_texto": "${:,.0f}".format(float(det["valor"])) if det["valor"] else "No definido",
        "nivel_alerta": nivel_alerta, "motivos_alerta": motivos_alerta,
        "incluir_alerta": incluir_alerta, "incluir_fechas": incluir_fechas,
        "incluir_comentarios": incluir_comentarios,
        "fechas_clave": (
            [("Fecha fin del convenio", det["fecha_fin_convenio"], True)]
            + (
                [
                    ("Límite liquidación voluntaria", det["fecha_limite_liquidacion_voluntaria"], False),
                    ("Límite liquidación unilateral", det["fecha_limite_liquidacion_unilateral"], False),
                    ("Límite liquidación judicial", det["fecha_limite_liquidacion_judicial"], False),
                    ("Vencimiento de póliza", det["fecha_vencimiento_poliza"], False),
                ]
                if det["estado"] == "En liquidación"
                else []
            )
        ),
        "periodos": periodos_contexto,
        "fecha_generacion": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "usuario_generador": usuario_nombre,
    }


@router.get("/periodo/{periodo_id}", summary="Datos del informe de un período específico (JSON)")
def informe_periodo_json(
    periodo_id: int,
    incluir_alerta: bool = True,
    incluir_fechas: bool = True,
    incluir_ejecucion: bool = True,
    incluir_liquidacion: bool = True,
    incluir_cierre: bool = True,
    incluir_comentarios: bool = True,
    user: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> Dict[str, Any]:
    with engine_analitica.connect() as conn:
        fila = conn.execute(
            text("SELECT convenio_id, periodo FROM convenio_periodos_seg_mc WHERE id=:pid"), {"pid": periodo_id}
        ).mappings().fetchone()
    if not fila:
        raise HTTPException(status_code=404, detail="Período no encontrado")

    det = _get_convenio_detalle_row(fila["convenio_id"])
    periodos_a_mostrar = [{"id": periodo_id, "periodo": fila["periodo"]}]
    titulo_informe = f"Informe · Período {fila['periodo']}"

    return _armar_contexto(
        det, periodos_a_mostrar, titulo_informe,
        incluir_alerta, incluir_fechas, incluir_ejecucion, incluir_liquidacion, incluir_cierre, incluir_comentarios,
        user.get("nombre", "usuario"),
    )


@router.get("/convenio/{convenio_id}", summary="Datos del informe consolidado de un convenio, todos sus períodos (JSON)")
def informe_convenio_json(
    convenio_id: int,
    incluir_alerta: bool = True,
    incluir_fechas: bool = True,
    incluir_ejecucion: bool = True,
    incluir_liquidacion: bool = True,
    incluir_cierre: bool = True,
    incluir_comentarios: bool = True,
    user: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> Dict[str, Any]:
    det = _get_convenio_detalle_row(convenio_id)
    periodos_a_mostrar = _get_periodos_convenio(convenio_id)
    titulo_informe = "Informe consolidado del convenio"

    return _armar_contexto(
        det, periodos_a_mostrar, titulo_informe,
        incluir_alerta, incluir_fechas, incluir_ejecucion, incluir_liquidacion, incluir_cierre, incluir_comentarios,
        user.get("nombre", "usuario"),
    )


@router.get("/periodo/{periodo_id}/pdf", summary="Informe de un período específico, en PDF")
def informe_periodo_pdf(
    periodo_id: int,
    incluir_alerta: bool = True,
    incluir_fechas: bool = True,
    incluir_ejecucion: bool = True,
    incluir_liquidacion: bool = True,
    incluir_cierre: bool = True,
    incluir_comentarios: bool = True,
    user: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> Response:
    contexto = informe_periodo_json(
        periodo_id, incluir_alerta, incluir_fechas, incluir_ejecucion, incluir_liquidacion, incluir_cierre,
        incluir_comentarios, user,
    )
    pdf_bytes = generar_pdf_informe(contexto)
    nombre_archivo = f"Informe_{contexto['codigo'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.get("/convenio/{convenio_id}/pdf", summary="Informe consolidado de un convenio, en PDF")
def informe_convenio_pdf(
    convenio_id: int,
    incluir_alerta: bool = True,
    incluir_fechas: bool = True,
    incluir_ejecucion: bool = True,
    incluir_liquidacion: bool = True,
    incluir_cierre: bool = True,
    incluir_comentarios: bool = True,
    user: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> Response:
    contexto = informe_convenio_json(
        convenio_id, incluir_alerta, incluir_fechas, incluir_ejecucion, incluir_liquidacion, incluir_cierre,
        incluir_comentarios, user,
    )
    pdf_bytes = generar_pdf_informe(contexto)
    nombre_archivo = f"Informe_{contexto['codigo'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
