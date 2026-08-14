"""
Helpers de negocio del módulo Seguimiento compartidos entre routers.
Portados tal cual de la app Streamlit (app/seguimiento/db.py y ui.py).
"""
from datetime import date
from typing import Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine


def crear_instancias_actividades(engine: Engine, convenio_id: int, convenio_periodo_id: int, tipo: str) -> int:
    """
    Crea las instancias de actividades del catálogo (tipo='ejecucion'|'liquidacion'|'cierre')
    para un período específico de un convenio. Idempotente (INSERT IGNORE):
    llamarla de nuevo (ej. tras agregar actividades al catálogo) no duplica
    las que ya existían. Retorna cuántas instancias nuevas insertó realmente
    (INSERT IGNORE no cuenta las que ya existían), para poder reportar el
    resultado de una sincronización (ver create_actividad_catalogo).
    """
    with engine.connect() as conn:
        resultado = conn.execute(
            text("""
                INSERT IGNORE INTO actividades_convenio_seg_mc
                    (convenio_id, convenio_periodo_id, actividad_base_id, estado, porcentaje_avance)
                SELECT :convenio_id, :convenio_periodo_id, id, 'Pendiente', 0
                FROM actividades_base_seg_mc
                WHERE tipo = :tipo
                ORDER BY orden
            """),
            {"convenio_id": convenio_id, "convenio_periodo_id": convenio_periodo_id, "tipo": tipo},
        )
        conn.commit()
        return resultado.rowcount


def preseed_notificaciones_pasadas(
    engine: Engine,
    convenio_id: int,
    f_liq_vol: Optional[date],
    f_liq_uni: Optional[date],
    f_liq_jud: Optional[date],
    f_pol: Optional[date],
) -> None:
    """
    Si alguna fecha límite calculada ya quedó en el pasado (convenios
    históricos), se marca como "ya notificada" para que n8n no dispare una
    alerta retroactiva. No afecta fechas futuras.
    """
    hoy = date.today()
    fechas_tipo = [
        (f_liq_vol, "voluntaria"),
        (f_liq_uni, "unilateral"),
        (f_liq_jud, "judicial_2m"),
        (f_liq_jud, "judicial_1m"),
        (f_liq_jud, "judicial_15d"),
        (f_pol, "poliza"),
    ]
    with engine.connect() as conn:
        for fecha, tipo in fechas_tipo:
            if fecha and fecha < hoy:
                conn.execute(
                    text("""
                        INSERT IGNORE INTO notificaciones_enviadas_seg_mc (convenio_id, tipo_notificacion)
                        VALUES (:convenio_id, :tipo)
                    """),
                    {"convenio_id": convenio_id, "tipo": tipo},
                )
        conn.commit()


def get_datos_alerta_secop_dtf(engine: Engine, convenio_id: int) -> Tuple[Optional[date], bool]:
    """
    (fecha_firma_dtf, secop_pendiente) para el semáforo de alertas:
    - fecha_firma_dtf: fecha más antigua en que se completó la actividad
      id=36 ("Firma director DTF") en cualquiera de los períodos del convenio.
    - secop_pendiente: True si existe la actividad id=23 (Publicación SECOP)
      y falta completarla en al menos un período.
    """
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT
                    MIN(CASE WHEN ab.id=36 AND ac.estado='Completada' THEN ac.fecha_completado END) AS fecha_firma_dtf,
                    SUM(CASE WHEN ab.id=23 THEN 1 ELSE 0 END) AS total_secop,
                    SUM(CASE WHEN ab.id=23 AND ac.estado='Completada' THEN 1 ELSE 0 END) AS completadas_secop
                FROM actividades_convenio_seg_mc ac
                JOIN actividades_base_seg_mc ab ON ac.actividad_base_id = ab.id
                WHERE ac.convenio_id = :convenio_id AND ab.id IN (23, 36)
            """),
            {"convenio_id": convenio_id},
        ).fetchone()

    if not row:
        return None, False
    fecha_firma_dtf, total_secop, completadas_secop = row
    secop_pendiente = bool(total_secop) and (completadas_secop or 0) < total_secop
    return fecha_firma_dtf, secop_pendiente


def calcular_nivel_alerta_convenio(
    engine: Engine,
    convenio_id: int,
    f_liq_vol: Optional[date],
    f_liq_uni: Optional[date],
    f_liq_jud: Optional[date],
    f_pol: Optional[date],
    fecha_firma_dg: Optional[date],
    estado: str,
) -> Tuple[Optional[str], list]:
    """
    Nivel de alerta más urgente vigente para un convenio, con los mismos
    umbrales usados en los correos de notificación de n8n.
    Retorna (nivel: 'AVISO'|'URGENTE'|'CRÍTICO'|None, motivos: [str, ...]).
    Solo aplica a convenios en estado 'En liquidación'.
    """
    if estado != "En liquidación":
        return None, []

    hoy = date.today()

    def dias_hasta(fecha):
        return (fecha - hoy).days if fecha else None

    niveles = []  # (rango 1=aviso 2=urgente 3=critico, motivo)

    d = dias_hasta(f_liq_jud)
    if d is not None:
        if d <= 15:
            niveles.append((3, "Liquidación judicial"))
        elif d <= 30:
            niveles.append((2, "Liquidación judicial"))
        elif d <= 60:
            niveles.append((1, "Liquidación judicial"))

    for fecha, nombre in [(f_liq_vol, "Liquidación voluntaria"), (f_liq_uni, "Liquidación unilateral")]:
        d = dias_hasta(fecha)
        if d is not None and d <= 10:
            niveles.append((1, nombre))

    d = dias_hasta(f_pol)
    if d is not None and d <= 30:
        niveles.append((1, "Vencimiento de póliza"))

    fecha_firma_dtf, secop_pendiente = get_datos_alerta_secop_dtf(engine, convenio_id)

    if fecha_firma_dtf and not fecha_firma_dg:
        niveles.append((1, "Confirmar firma Director General"))

    if fecha_firma_dg and secop_pendiente:
        dias_transcurridos = (hoy - fecha_firma_dg).days
        dias_restantes = 3 - dias_transcurridos
        if dias_restantes >= 3:
            niveles.append((1, "Publicación SECOP"))
        elif dias_restantes >= 1:
            niveles.append((2, "Publicación SECOP"))
        else:
            niveles.append((3, "Publicación SECOP"))

    if not niveles:
        return None, []

    max_rango = max(n[0] for n in niveles)
    motivos = [n[1] for n in niveles if n[0] == max_rango]
    nombre_nivel = {1: "AVISO", 2: "URGENTE", 3: "CRÍTICO"}[max_rango]
    return nombre_nivel, motivos
