"""
Helpers para el informe de estado de un período/convenio — portados tal cual
de app/seguimiento/ui.py (get_historial_comentarios_periodo,
get_datos_informe_periodo, texto_fecha_estado, generar_pdf_informe).
"""
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

ROL_LABELS = {
    "ADMIN": "Administrador",
    "DIRECTORA": "Directora",
    "LMC": "Líder de Programa MC (LMC)",
    "AST": "Apoyo Supervisión Técnica (AST)",
    "AD": "Apoyo de Datos (AD)",
    "AF": "Apoyo Financiero (AF)",
    "AJ": "Apoyo Jurídico (AJ)",
}


def _get_actividades_periodo(engine: Engine, convenio_periodo_id: int, tipo: str) -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT ab.id AS actividad_base_id, ab.nombre, ab.subcategoria, ab.subcategoria_orden, ab.orden,
                       ab.es_relevante, ab.tiene_fecha_limite,
                       ac.id AS actividad_convenio_id, ac.estado, ac.porcentaje_avance, ac.ultimo_comentario,
                       ac.ultima_actualizacion, u.nombre AS resp_nombre, u.rol AS resp_rol,
                       ac.fecha_completado, COALESCE(ac.no_aplica, 0) AS no_aplica
                FROM actividades_base_seg_mc ab
                LEFT JOIN actividades_convenio_seg_mc ac
                    ON ac.actividad_base_id = ab.id AND ac.convenio_periodo_id = :pid
                LEFT JOIN usuarios_seg_proceso_mc u ON ac.responsable_id = u.id
                WHERE ab.tipo = :tipo
                ORDER BY ab.orden
            """),
            {"pid": convenio_periodo_id, "tipo": tipo},
        ).mappings().all()
    return [dict(r) for r in rows]


def _get_progreso_periodo(engine: Engine, convenio_periodo_id: int, tipo: str) -> int:
    with engine.connect() as conn:
        resultado = conn.execute(
            text("""
                SELECT ROUND(AVG(ac.porcentaje_avance), 0) AS promedio
                FROM actividades_convenio_seg_mc ac
                JOIN actividades_base_seg_mc ab ON ac.actividad_base_id = ab.id
                WHERE ac.convenio_periodo_id = :pid AND ab.tipo = :tipo AND ab.es_relevante = 1
            """),
            {"pid": convenio_periodo_id, "tipo": tipo},
        ).scalar()
    return int(resultado) if resultado is not None else 0


def get_historial_comentarios_periodo(engine: Engine, convenio_periodo_id: int) -> Dict[int, List[Tuple]]:
    with engine.connect() as conn:
        registros = conn.execute(
            text("""
                SELECT h.actividad_convenio_id, h.fecha_cambio, h.usuario_nombre, h.comentario
                FROM historial_actividades_seg_mc h
                JOIN actividades_convenio_seg_mc ac ON h.actividad_convenio_id = ac.id
                WHERE ac.convenio_periodo_id = :pid AND h.comentario IS NOT NULL AND h.comentario != ''
                ORDER BY h.actividad_convenio_id, h.fecha_cambio DESC
            """),
            {"pid": convenio_periodo_id},
        ).all()
    historial: Dict[int, List[Tuple]] = {}
    for act_id, fecha, usuario, comentario in registros:
        historial.setdefault(act_id, []).append((fecha, usuario, comentario))
    return historial


def get_datos_informe_periodo(engine: Engine, convenio_periodo_id: int) -> Dict[str, Any]:
    """
    Retorna un dict con todo lo necesario para el informe de un período:
    actividades agrupadas por tipo→subcategoría, con su historial completo de
    comentarios, y contadores de resumen por tipo. Réplica exacta de
    ui.py::get_datos_informe_periodo.
    """
    historial = get_historial_comentarios_periodo(engine, convenio_periodo_id)
    resultado: Dict[str, Any] = {}
    for tipo in ("ejecucion", "liquidacion", "cierre"):
        actividades = _get_actividades_periodo(engine, convenio_periodo_id, tipo)
        subcats: Dict[str, Any] = {}
        contadores = {"Completada": 0, "En curso": 0, "Pendiente": 0, "Bloqueada": 0, "Atrasada": 0, "No aplica": 0}
        for a in actividades:
            subcat = a["subcategoria"]
            if subcat not in subcats:
                subcats[subcat] = {"sub_orden": a["subcategoria_orden"], "acts": []}
            comentarios_hist = historial.get(a["actividad_convenio_id"], [])
            estado = a["estado"] or "Pendiente"
            no_aplica = bool(a["no_aplica"])
            subcats[subcat]["acts"].append({
                "orden": a["orden"], "nombre": a["nombre"], "estado": estado,
                "pct": a["porcentaje_avance"] or 0, "es_relevante": bool(a["es_relevante"]), "no_aplica": no_aplica,
                "resp_nombre": a["resp_nombre"], "resp_rol": a["resp_rol"],
                "ultima_act": a["ultima_actualizacion"], "fecha_completado": a["fecha_completado"],
                "comentarios": comentarios_hist,
            })
            if no_aplica:
                contadores["No aplica"] += 1
            else:
                contadores[estado] = contadores.get(estado, 0) + 1
        resultado[tipo] = {
            "subcats": subcats,
            "contadores": contadores,
            "pct_global": _get_progreso_periodo(engine, convenio_periodo_id, tipo),
            "total": len(actividades),
        }
    return resultado


def texto_fecha_estado(fecha: Optional[date], es_neutral: bool = False) -> Tuple[str, str]:
    """Texto plano + color hex para el estado de una fecha (usado en el PDF)."""
    if not fecha:
        return "No definida", "#6B7280"
    dias = (fecha - date.today()).days
    if es_neutral:
        if dias < 0:
            return f"Finalizó hace {abs(dias)} días", "#374151"
        elif dias == 0:
            return "Finaliza hoy", "#374151"
        else:
            return f"Faltan {dias} días", "#374151"
    if dias < 0:
        return f"Venció hace {abs(dias)} días", "#B91C1C"
    elif dias <= 15:
        return f"Faltan {dias} días", "#B91C1C"
    elif dias <= 30:
        return f"Faltan {dias} días", "#B45309"
    else:
        return f"Faltan {dias} días", "#15803D"


def generar_pdf_informe(contexto: Dict[str, Any]) -> bytes:
    """
    Construye el informe formal en PDF con reportlab a partir del dict
    `contexto`. Retorna los bytes del PDF. Portado tal cual de
    ui.py::generar_pdf_informe.
    """
    import io

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
        title=contexto["titulo"],
    )
    styles = getSampleStyleSheet()
    azul = colors.HexColor("#1A2B4A")
    gris = colors.HexColor("#6B7280")
    borde = colors.HexColor("#D5D0C6")

    st_titulo = ParagraphStyle("TituloInf", parent=styles["Title"], fontSize=17, textColor=azul, spaceAfter=2, alignment=0)
    st_subtitulo = ParagraphStyle("SubtituloInf", parent=styles["Normal"], fontSize=10, textColor=gris, spaceAfter=2)
    st_h2 = ParagraphStyle("H2Inf", parent=styles["Heading2"], fontSize=13, textColor=azul, spaceBefore=16, spaceAfter=6)
    st_h3 = ParagraphStyle("H3Inf", parent=styles["Heading3"], fontSize=10.5, textColor=colors.HexColor("#374151"), spaceBefore=10, spaceAfter=4)
    st_normal = ParagraphStyle("NormalInf", parent=styles["Normal"], fontSize=9.5, leading=13)
    st_comentario = ParagraphStyle("ComentarioInf", parent=styles["Normal"], fontSize=8.3, leftIndent=10, textColor=colors.HexColor("#4B5563"), spaceAfter=2, leading=11)
    st_resp = ParagraphStyle("RespInf", parent=styles["Normal"], fontSize=7.8, leading=9.5)

    story = []
    story.append(Paragraph(contexto["titulo"], st_titulo))
    story.append(Paragraph(f"{contexto['codigo']} &mdash; {contexto['ies_nombre']}", st_subtitulo))
    story.append(Paragraph(f"Generado el {contexto['fecha_generacion']} por {contexto['usuario_generador']}", st_subtitulo))
    story.append(Spacer(1, 10))

    story.append(Paragraph("INFORMACIÓN GENERAL", st_h2))
    filas_info = [
        ["Código", contexto["codigo"]],
        ["Institución", contexto["ies_nombre"] + (f" ({contexto['sigla']})" if contexto["sigla"] else "")],
        ["Estado actual", contexto["estado"]],
        ["Período(s)", contexto["periodo_texto"]],
        ["Supervisor", contexto["supervisor"] or "No asignado"],
        ["Apoyo a la supervisión", contexto["apoyo"] or "No asignado"],
        ["Valor del convenio", contexto["valor_texto"]],
    ]
    t_info = Table(filas_info, colWidths=[5.5 * cm, 10.5 * cm])
    t_info.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), azul),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, borde),
    ]))
    story.append(t_info)

    if contexto["incluir_alerta"] and contexto["nivel_alerta"]:
        story.append(Paragraph("ALERTA ACTIVA", st_h2))
        color_alerta = {"AVISO": "#B45309", "URGENTE": "#C2410C", "CRÍTICO": "#B91C1C"}.get(contexto["nivel_alerta"], "#374151")
        story.append(Paragraph(
            f"Nivel: <font color='{color_alerta}'><b>{contexto['nivel_alerta']}</b></font> &mdash; "
            f"Motivo(s): {', '.join(contexto['motivos_alerta'])}", st_normal
        ))

    if contexto["incluir_fechas"]:
        story.append(Paragraph("FECHAS CLAVE", st_h2))
        filas_fechas = [["Concepto", "Fecha", "Estado"]]
        for etiqueta, fecha, es_neutral in contexto["fechas_clave"]:
            texto_estado, color_hex = texto_fecha_estado(fecha, es_neutral=es_neutral)
            filas_fechas.append([etiqueta, str(fecha) if fecha else "No definida",
                                  Paragraph(f"<font color='{color_hex}'>{texto_estado}</font>", st_normal)])
        t_fechas = Table(filas_fechas, colWidths=[6 * cm, 3.5 * cm, 6.5 * cm])
        t_fechas.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("BACKGROUND", (0, 0), (-1, 0), azul),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.4, borde),
        ]))
        story.append(t_fechas)

    for periodo_bloque in contexto["periodos"]:
        if len(contexto["periodos"]) > 1:
            story.append(Paragraph(f"PERÍODO {periodo_bloque['label'].upper()}", st_h2))

        for tipo_bloque in periodo_bloque["tipos"]:
            story.append(Paragraph(
                f"ACTIVIDADES DE {tipo_bloque['etiqueta'].upper()} &mdash; {tipo_bloque['pct_global']}% completado",
                st_h2 if len(periodo_bloque["tipos"]) == 1 and len(contexto["periodos"]) == 1 else st_h3
            ))

            if tipo_bloque["total"] == 0:
                story.append(Paragraph("Sin actividades asignadas a este período.", st_normal))
                continue

            for subcat in tipo_bloque["subcats"]:
                story.append(Paragraph(subcat["nombre"], st_h3))
                filas_act = [["#", "Actividad", "Estado", "Avance", "Responsable del estado"]]
                for act in subcat["acts"]:
                    estado_txt = "No aplica" if act["no_aplica"] else act["estado"]
                    filas_act.append([
                        str(act["orden"]),
                        Paragraph(act["nombre"], st_normal),
                        estado_txt,
                        f"{act['pct']}%",
                        Paragraph(act["resp_nombre"] or "Sin asignar", st_resp),
                    ])
                t_act = Table(filas_act, colWidths=[0.8 * cm, 7.2 * cm, 2.0 * cm, 1.3 * cm, 4.7 * cm])
                t_act.setStyle(TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 8.3),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9E5DC")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.4, borde),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(t_act)

                if contexto["incluir_comentarios"]:
                    for act in subcat["acts"]:
                        if act["comentarios"]:
                            story.append(Spacer(1, 3))
                            for fecha_c, usuario_c, texto_c in act["comentarios"]:
                                story.append(Paragraph(
                                    f"<b>{act['nombre'][:45]}</b> &mdash; {usuario_c} ({str(fecha_c)[:16]}): {texto_c}",
                                    st_comentario
                                ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
