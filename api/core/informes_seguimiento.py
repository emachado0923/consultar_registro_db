"""
Helpers para el informe de estado de un período/convenio — portados tal cual
de app/seguimiento/ui.py (get_historial_comentarios_periodo,
get_datos_informe_periodo, texto_fecha_estado, generar_pdf_informe).
"""
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape
 
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
        # % y conteo por estado a nivel de SUBCATEGORÍA (nuevo, para el
        # "resumen ejecutivo" del informe) — mismo criterio que
        # _get_progreso_periodo (solo es_relevante=1) y que el conteo por
        # tipo de arriba, pero agregado por subcategoría en vez de global.
        for info in subcats.values():
            acts_relevantes = [a for a in info["acts"] if a["es_relevante"]]
            info["pct"] = round(sum(a["pct"] for a in acts_relevantes) / len(acts_relevantes)) if acts_relevantes else 0
            conteo_subcat = {"Completada": 0, "En curso": 0, "Pendiente": 0, "Bloqueada": 0, "Atrasada": 0, "No aplica": 0}
            for a in info["acts"]:
                if a["no_aplica"]:
                    conteo_subcat["No aplica"] += 1
                else:
                    conteo_subcat[a["estado"]] = conteo_subcat.get(a["estado"], 0) + 1
            info["contadores"] = conteo_subcat
 
            # Último comentario registrado en la subcategoría (el más reciente
            # entre todas sus actividades), para mostrarlo directamente en el
            # resumen ejecutivo — reemplaza al antiguo checkbox de "historial
            # de comentarios" por algo siempre visible y más útil de un
            # vistazo. Cada `a["comentarios"]` ya viene ordenado DESC por
            # fecha (ver get_historial_comentarios_periodo), así que el más
            # reciente de cada actividad es el primer elemento.
            ultimo = None
            for a in info["acts"]:
                if a["comentarios"]:
                    fecha_c, usuario_c, texto_c = a["comentarios"][0]
                    if ultimo is None or fecha_c > ultimo["fecha"]:
                        ultimo = {"fecha": fecha_c, "usuario": usuario_c, "comentario": texto_c, "actividad": a["nombre"]}
            info["ultimo_comentario"] = ultimo
 
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
 
 
def procesar_imagen_para_pdf(datos_imagen: bytes, lado_max_px: int = 1600, calidad_jpeg: int = 85) -> "io.BytesIO":
    """
    Prepara una imagen subida por el usuario (evidencia de una subcategoría,
    solo para ESTE PDF puntual — nunca se guarda en disco ni en la BD) para
    insertarla con reportlab:
 
    - Corrige la rotación según el tag EXIF de orientación. Las fotos de
      celular casi siempre traen los píxeles "acostados" con ese tag
      diciendo cómo rotarlos al mostrarlas; reportlab/Pillow ignoran ese tag
      por defecto, así que sin este paso muchas fotos saldrían giradas
      90°/180° en el informe.
    - Aplana el canal alfa (PNG/webp con transparencia) sobre fondo blanco:
      re-codificamos siempre a JPEG (liviano, universal, reportlab lo lee
      sin dependencias extra) y JPEG no soporta transparencia — sin este
      paso las zonas transparentes saldrían en negro.
    - Reduce el tamaño si excede `lado_max_px` en el lado más largo: una
      foto de celular de 12+ megapíxeles no aporta nada en una página que la
      va a mostrar del tamaño de una estampilla, y solo infla el PDF.
 
    Lanza ValueError si los bytes no son una imagen legible — el llamador
    debe capturarlo y descartar esa imagen puntual (con un aviso) en vez de
    hacer fallar la generación de todo el informe.
    """
    import io
 
    from PIL import Image as PILImage
    from PIL import ImageOps
 
    try:
        imagen = PILImage.open(io.BytesIO(datos_imagen))
        imagen.load()
    except Exception as exc:  # Pillow lanza distintos tipos según el problema
        raise ValueError(f"No se pudo leer como imagen: {exc}") from exc
 
    imagen = ImageOps.exif_transpose(imagen)
 
    if imagen.mode in ("RGBA", "LA") or (imagen.mode == "P" and "transparency" in imagen.info):
        base_blanca = PILImage.new("RGB", imagen.size, (255, 255, 255))
        imagen_rgba = imagen.convert("RGBA")
        base_blanca.paste(imagen_rgba, mask=imagen_rgba.split()[-1])
        imagen = base_blanca
    elif imagen.mode != "RGB":
        imagen = imagen.convert("RGB")
 
    imagen.thumbnail((lado_max_px, lado_max_px), PILImage.LANCZOS)
 
    salida = io.BytesIO()
    imagen.save(salida, format="JPEG", quality=calidad_jpeg, optimize=True)
    salida.seek(0)
    return salida
 
 
def _construir_grid_imagenes(imagenes_bytesio: List["io.BytesIO"]):
    """
    Arma una cuadrícula de imágenes ya procesadas (ver `procesar_imagen_para_pdf`)
    para insertar en el PDF, con "contain-fit": cada imagen se escala para
    CABER dentro de su celda preservando su proporción real (sin distorsión,
    sin recorte) — el tamaño de celda se adapta según cuántas imágenes hay
    para que una sola foto no quede diminuta ni tres fotos queden gigantes.
    """
    from reportlab.lib.units import cm
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus import Table, TableStyle
    from PIL import Image as PILImage
 
    if not imagenes_bytesio:
        return None
 
    # (columnas, ancho_celda, alto_celda) según cuántas imágenes hay en esta subcategoría.
    columnas = min(len(imagenes_bytesio), 3)
    ancho_celda, alto_celda = {
        1: (10.5 * cm, 9.5 * cm),
        2: (8.0 * cm, 7.5 * cm),
        3: (5.4 * cm, 5.4 * cm),
    }[columnas]
 
    celdas = []
    for buf in imagenes_bytesio:
        buf.seek(0)
        ancho_px, alto_px = PILImage.open(buf).size
        buf.seek(0)
        escala = min(ancho_celda / ancho_px, alto_celda / alto_px)
        celdas.append(RLImage(buf, width=ancho_px * escala, height=alto_px * escala))
 
    filas = [celdas[i : i + columnas] for i in range(0, len(celdas), columnas)]
    tabla = Table(filas, colWidths=[ancho_celda] * columnas)
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tabla
 
 
def _construir_barra_pct(pct: int, ancho):
    """Barrita horizontal de progreso (2 celdas coloreadas) para el resumen ejecutivo."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
 
    pct = max(0, min(100, pct))
    color = colors.HexColor("#B91C1C") if pct < 40 else colors.HexColor("#B45309") if pct < 80 else colors.HexColor("#15803D")
    fondo = colors.HexColor("#E9E5DC")
    ancho_lleno = ancho * (pct / 100)
    ancho_vacio = ancho - ancho_lleno
 
    if ancho_lleno <= 0:
        tabla = Table([[""]], colWidths=[ancho], rowHeights=[6])
        tabla.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), fondo)]))
    elif ancho_vacio <= 0:
        tabla = Table([[""]], colWidths=[ancho], rowHeights=[6])
        tabla.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), color)]))
    else:
        tabla = Table([["", ""]], colWidths=[ancho_lleno, ancho_vacio], rowHeights=[6])
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), color),
            ("BACKGROUND", (1, 0), (1, 0), fondo),
        ]))
    tabla.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tabla
 
 
def generar_pdf_informe(contexto: Dict[str, Any], notas_comentarios: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None) -> bytes:
    """
    Construye el informe formal en PDF con reportlab a partir del dict
    `contexto` (portado originalmente de ui.py::generar_pdf_informe, luego
    ampliado con un resumen ejecutivo por subcategoría y una sección de
    comentarios/evidencias). Retorna los bytes del PDF.
 
    `notas_comentarios`: dict opcional {(tipo, subcategoria): {"comentario": str, "imagenes": [bytes, ...]}}
    con lo que el usuario escribió/adjuntó en el modal justo antes de generar
    este informe puntual — NO viene de ninguna tabla, no se persiste en
    ningún lado antes ni después de esta llamada.
    """
    import io
 
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
 
    notas_comentarios = notas_comentarios or {}
 
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
 
        incluir_resumen = contexto.get("incluir_resumen_ejecutivo", True)
        incluir_detalle = contexto.get("incluir_detalle_actividades", False)
 
        for tipo_bloque in periodo_bloque["tipos"]:
            story.append(Paragraph(
                f"ACTIVIDADES DE {tipo_bloque['etiqueta'].upper()} &mdash; {tipo_bloque['pct_global']}% completado",
                st_h2 if len(periodo_bloque["tipos"]) == 1 and len(contexto["periodos"]) == 1 else st_h3
            ))
 
            if tipo_bloque["total"] == 0:
                story.append(Paragraph("Sin actividades asignadas a este período.", st_normal))
                continue
 
            # ---- Resumen ejecutivo: % y conteos por subcategoría, en vez de
            # ---- volcar cada actividad una por una (esto reemplaza al
            # ---- listado plano como la vista PRINCIPAL del informe). ----
            if incluir_resumen:
                ANCHO_BARRA = 4.0 * cm
                filas_resumen = [["Subcategoría", "%", "Progreso", "Compl.", "En curso", "Pend."]]
                filas_barra = {}  # fila -> flowable de la barra, para insertarlo después de construir la tabla
                # Filas (índices) que son de "último comentario" en vez de datos
                # de subcategoría — se les aplica SPAN + estilo propio más
                # abajo. Reemplaza al antiguo checkbox de "historial de
                # comentarios" (que solo aparecía si además se activaba el
                # detalle actividad-por-actividad) por algo siempre visible,
                # directamente en el resumen ejecutivo.
                filas_comentario = []
                for sc in tipo_bloque["subcats"]:
                    pct = sc.get("pct", 0)
                    cont = sc.get("contadores", {})
                    fila_idx = len(filas_resumen)
                    filas_barra[fila_idx] = _construir_barra_pct(pct, ANCHO_BARRA)
                    filas_resumen.append([
                        Paragraph(sc["nombre"], st_normal), f"{pct}%", "",
                        str(cont.get("Completada", 0)), str(cont.get("En curso", 0)),
                        str(cont.get("Pendiente", 0)),
                    ])
                    ultimo = sc.get("ultimo_comentario")
                    if ultimo:
                        # Texto dinámico (nombre de actividad, usuario, comentario)
                        # viene de datos escritos libremente por usuarios, así que
                        # se escapa antes de meterlo en el markup XML de
                        # Paragraph — un "<" o "&" sueltos en un comentario real
                        # tumbarían la generación completa del informe si no se
                        # escapan.
                        actividad_esc = xml_escape(ultimo["actividad"] or "")
                        usuario_esc = xml_escape(ultimo["usuario"] or "Sin usuario")
                        comentario_esc = xml_escape(ultimo["comentario"] or "")
                        fecha_str = str(ultimo["fecha"])[:16]
                        # Nota: sin emoji — la fuente estándar (Helvetica, vía
                        # reportlab) no tiene esos glifos y se veían como un
                        # cuadro vacío en el PDF final; se usa texto en
                        # mayúsculas + el mismo tono gris de st_comentario en
                        # su lugar.
                        texto = (
                            f"<b>ÚLTIMO COMENTARIO</b> &mdash; {actividad_esc} · "
                            f"{usuario_esc} ({fecha_str}): {comentario_esc}"
                        )
                        filas_comentario.append(len(filas_resumen))
                        filas_resumen.append([Paragraph(texto, st_comentario), "", "", "", "", ""])
                for fila_idx, barra in filas_barra.items():
                    filas_resumen[fila_idx][2] = barra
                t_resumen = Table(
                    filas_resumen,
                    colWidths=[6.5 * cm, 0.9 * cm, ANCHO_BARRA + 0.2 * cm, 1.4 * cm, 1.5 * cm, 1.3 * cm],
                )
                estilo_resumen = [
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9E5DC")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.4, borde),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
                # Overrides para las filas de "último comentario" — van
                # DESPUÉS del estilo base en la lista para que tengan
                # prioridad sobre él en esas celdas puntuales.
                for fila_idx in filas_comentario:
                    estilo_resumen.extend([
                        ("SPAN", (0, fila_idx), (-1, fila_idx)),
                        ("BACKGROUND", (0, fila_idx), (-1, fila_idx), colors.HexColor("#F9FAFB")),
                        ("ALIGN", (0, fila_idx), (-1, fila_idx), "LEFT"),
                        ("TOPPADDING", (0, fila_idx), (-1, fila_idx), 3),
                        ("BOTTOMPADDING", (0, fila_idx), (-1, fila_idx), 5),
                    ])
                t_resumen.setStyle(TableStyle(estilo_resumen))
                story.append(t_resumen)
                story.append(Spacer(1, 8))
 
            # ---- Detalle actividad-por-actividad: ahora OPCIONAL (antes era
            # ---- lo único que mostraba el informe). ----
            if incluir_detalle:
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
 
            # ---- Comentarios y evidencias por subcategoría: lo que el
            # ---- usuario escribió/adjuntó en el modal justo antes de
            # ---- generar ESTE informe (no viene de ninguna tabla). ----
            subcats_con_nota = [
                sc for sc in tipo_bloque["subcats"]
                if (tipo_bloque.get("tipo"), sc["nombre"]) in notas_comentarios
            ]
            if subcats_con_nota:
                story.append(Paragraph("Comentarios y evidencias", st_h3))
                for sc in subcats_con_nota:
                    nota = notas_comentarios[(tipo_bloque.get("tipo"), sc["nombre"])]
                    story.append(Paragraph(f"<b>{sc['nombre']}</b>", st_normal))
                    if nota.get("comentario"):
                        story.append(Paragraph(nota["comentario"], st_normal))
                    imagenes_bytesio = []
                    for datos_imagen in nota.get("imagenes", []):
                        try:
                            imagenes_bytesio.append(procesar_imagen_para_pdf(datos_imagen))
                        except ValueError:
                            # imagen corrupta/no soportada: se omite en vez de
                            # tumbar la generación completa del informe.
                            continue
                    grid = _construir_grid_imagenes(imagenes_bytesio)
                    if grid is not None:
                        story.append(Spacer(1, 4))
                        story.append(grid)
                    story.append(Spacer(1, 10))
 
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()