from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from ..core.database import engine_analitica
from ..models.seguimiento_actividades import (
    ActividadPeriodoOut,
    AvanceResponse,
    AvanceUpdateRequest,
    NoAplicaRequest,
    RecordatorioUpdateRequest,
)
from .seguimiento_auth import get_current_user_seguimiento, require_rol

router = APIRouter(prefix="/seguimiento", tags=["Seguimiento · Actividades"])

TIPOS_VALIDOS = ("ejecucion", "liquidacion", "cierre")

# Cadena de transiciones automáticas de estado del convenio — idéntica a
# app/seguimiento/ui.py::TRANSICION_ESTADO. 'ejecucion' NO está aquí a
# propósito: ese paso lo dispara el flujo diario de n8n por fecha_fin_convenio.
TRANSICION_ESTADO = {
    "liquidacion": ("En liquidación", "En cierre"),
    "cierre": ("En cierre", "Cerrado"),
}


def _validar_tipo(tipo: str) -> None:
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"tipo debe ser uno de {TIPOS_VALIDOS}")


def _verificar_avance_automatico_convenio(convenio_id: int, tipo_actividad: str) -> AvanceResponse:
    """Réplica exacta de ui.py::_verificar_avance_automatico_convenio."""
    if tipo_actividad not in TRANSICION_ESTADO:
        return AvanceResponse(avanzo_estado_convenio=False)

    estado_esperado, estado_siguiente = TRANSICION_ESTADO[tipo_actividad]

    with engine_analitica.connect() as conn:
        conteo = conn.execute(
            text("""
                SELECT
                    SUM(CASE WHEN ab.es_relevante = 1 THEN 1 ELSE 0 END) AS total_relevantes,
                    SUM(CASE WHEN ab.es_relevante = 1 AND ac.estado = 'Completada' THEN 1 ELSE 0 END) AS completadas_relevantes,
                    c.estado AS estado_actual, c.codigo
                FROM actividades_convenio_seg_mc ac
                JOIN actividades_base_seg_mc ab ON ac.actividad_base_id = ab.id
                JOIN convenios_seg_proceso_mc c ON ac.convenio_id = c.id
                WHERE ac.convenio_id = :cid AND ab.tipo = :tipo
                GROUP BY c.estado, c.codigo
            """),
            {"cid": convenio_id, "tipo": tipo_actividad},
        ).mappings().fetchone()

        if not conteo:
            return AvanceResponse(avanzo_estado_convenio=False)

        total_relevantes = conteo["total_relevantes"]
        completadas_relevantes = conteo["completadas_relevantes"]
        estado_actual = conteo["estado_actual"]
        codigo = conteo["codigo"]

        if total_relevantes and completadas_relevantes == total_relevantes and estado_actual == estado_esperado:
            conn.execute(
                text("UPDATE convenios_seg_proceso_mc SET estado=:estado WHERE id=:cid"),
                {"estado": estado_siguiente, "cid": convenio_id},
            )
            conn.commit()
            return AvanceResponse(avanzo_estado_convenio=True, codigo_convenio=codigo, nuevo_estado_convenio=estado_siguiente)

    return AvanceResponse(avanzo_estado_convenio=False)


@router.get("/periodos/{periodo_id}/actividades", response_model=List[ActividadPeriodoOut], summary="Listar actividades de un período (por tipo)")
def list_actividades_periodo(
    periodo_id: int,
    tipo: str = "liquidacion",
    solo_relevantes: bool = False,
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
):
    _validar_tipo(tipo)
    rel_filter = "AND ab.es_relevante=1" if solo_relevantes else ""
    with engine_analitica.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT ab.id AS actividad_base_id, ab.nombre, ab.subcategoria, ab.subcategoria_orden, ab.orden,
                       ab.es_relevante, ab.tiene_fecha_limite,
                       ac.id AS actividad_convenio_id, ac.estado, ac.porcentaje_avance, ac.ultimo_comentario,
                       ac.ultima_actualizacion, u.nombre AS responsable_nombre, u.rol AS responsable_rol,
                       ac.fecha_completado, COALESCE(ac.no_aplica, 0) AS no_aplica,
                       ac.fecha_recordatorio, ac.nota_recordatorio
                FROM actividades_base_seg_mc ab
                LEFT JOIN actividades_convenio_seg_mc ac
                    ON ac.actividad_base_id = ab.id AND ac.convenio_periodo_id = :periodo_id
                LEFT JOIN usuarios_seg_proceso_mc u ON ac.responsable_id = u.id
                WHERE ab.tipo = :tipo {rel_filter}
                ORDER BY ab.orden
            """),
            {"periodo_id": periodo_id, "tipo": tipo},
        ).mappings().all()

    resultado = []
    for r in rows:
        d = dict(r)
        d["estado"] = d["estado"] or "Pendiente"
        d["porcentaje_avance"] = d["porcentaje_avance"] or 0
        d["no_aplica"] = bool(d["no_aplica"])
        resultado.append(d)
    return resultado


@router.patch("/actividades/{actividad_convenio_id}/avance", response_model=AvanceResponse, summary="Guardar avance de una actividad (equivalente a guardar_avance)")
def update_avance(
    actividad_convenio_id: int,
    data: AvanceUpdateRequest,
    user: Dict[str, Any] = Depends(get_current_user_seguimiento),
):
    if user.get("rol") == "DIRECTORA":
        raise HTTPException(status_code=403, detail="El rol Directora no puede editar actividades")

    campos_enviados = data.dict(exclude_unset=True)

    with engine_analitica.connect() as conn:
        prev = conn.execute(
            text("""
                SELECT estado, porcentaje_avance, convenio_id, actividad_base_id, fecha_recordatorio, nota_recordatorio
                FROM actividades_convenio_seg_mc WHERE id=:id
            """),
            {"id": actividad_convenio_id},
        ).mappings().fetchone()
        if not prev:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")

        est_ant = prev["estado"] or "Pendiente"
        pct_ant = prev["porcentaje_avance"] or 0
        convenio_id = prev["convenio_id"]
        actividad_base_id = prev["actividad_base_id"]
        fecha_recordatorio_previa = prev["fecha_recordatorio"]
        nota_recordatorio_previa = prev["nota_recordatorio"]

        tipo_actividad = None
        if actividad_base_id is not None:
            fila_tipo = conn.execute(
                text("SELECT tipo FROM actividades_base_seg_mc WHERE id=:id"), {"id": actividad_base_id}
            ).mappings().fetchone()
            tipo_actividad = fila_tipo["tipo"] if fila_tipo else None

        nuevo_pct = data.porcentaje_avance
        if nuevo_pct == 0:
            nuevo_estado = "Pendiente"
        elif nuevo_pct == 100:
            nuevo_estado = "Completada"
        else:
            nuevo_estado = "En curso"

        fecha_completado = None
        if nuevo_estado == "Completada":
            fecha_completado = data.fecha_manual if data.fecha_manual else date.today()

        # Si el caller no envió recordatorio explícitamente, se preserva el valor
        # ya guardado (igual que el formulario de Streamlit, que administra el
        # recordatorio aparte y solo reenvía el valor sin cambios).
        fecha_recordatorio = campos_enviados.get("fecha_recordatorio", fecha_recordatorio_previa)
        nota_recordatorio = campos_enviados.get("nota_recordatorio", nota_recordatorio_previa)
        recordatorio_enviado = 0 if fecha_recordatorio != fecha_recordatorio_previa else None

        if recordatorio_enviado is None:
            conn.execute(
                text("""
                    UPDATE actividades_convenio_seg_mc
                    SET estado=:estado, porcentaje_avance=:pct, ultimo_comentario=:comentario,
                        responsable_id=:responsable_id, fecha_completado=:fecha_completado,
                        fecha_recordatorio=:fecha_recordatorio, nota_recordatorio=:nota_recordatorio
                    WHERE id=:id
                """),
                {
                    "estado": nuevo_estado, "pct": nuevo_pct, "comentario": data.comentario,
                    "responsable_id": user["usuario_id"], "fecha_completado": fecha_completado,
                    "fecha_recordatorio": fecha_recordatorio, "nota_recordatorio": nota_recordatorio,
                    "id": actividad_convenio_id,
                },
            )
        else:
            conn.execute(
                text("""
                    UPDATE actividades_convenio_seg_mc
                    SET estado=:estado, porcentaje_avance=:pct, ultimo_comentario=:comentario,
                        responsable_id=:responsable_id, fecha_completado=:fecha_completado,
                        fecha_recordatorio=:fecha_recordatorio, nota_recordatorio=:nota_recordatorio,
                        recordatorio_enviado=:recordatorio_enviado
                    WHERE id=:id
                """),
                {
                    "estado": nuevo_estado, "pct": nuevo_pct, "comentario": data.comentario,
                    "responsable_id": user["usuario_id"], "fecha_completado": fecha_completado,
                    "fecha_recordatorio": fecha_recordatorio, "nota_recordatorio": nota_recordatorio,
                    "recordatorio_enviado": recordatorio_enviado, "id": actividad_convenio_id,
                },
            )

        conn.execute(
            text("""
                INSERT INTO historial_actividades_seg_mc
                    (actividad_convenio_id, usuario_id, usuario_nombre,
                     estado_anterior, estado_nuevo, porcentaje_anterior, porcentaje_nuevo, comentario)
                VALUES (:acid, :uid, :unombre, :est_ant, :est_nuevo, :pct_ant, :pct_nuevo, :comentario)
            """),
            {
                "acid": actividad_convenio_id, "uid": user["usuario_id"], "unombre": user["nombre"],
                "est_ant": est_ant, "est_nuevo": nuevo_estado, "pct_ant": pct_ant, "pct_nuevo": nuevo_pct,
                "comentario": data.comentario,
            },
        )

        # Sincronizar fecha_firma_director_general con la actividad id=22.
        if actividad_base_id == 22 and convenio_id is not None:
            conn.execute(
                text("UPDATE convenios_seg_proceso_mc SET fecha_firma_director_general=:f WHERE id=:cid"),
                {"f": fecha_completado, "cid": convenio_id},
            )

        conn.commit()

    if convenio_id is None:
        return AvanceResponse(avanzo_estado_convenio=False)
    return _verificar_avance_automatico_convenio(convenio_id, tipo_actividad)


@router.patch("/actividades/{actividad_convenio_id}/no-aplica", response_model=AvanceResponse, summary="Marcar/revertir 'No aplica' (equivalente a marcar_no_aplica)")
def update_no_aplica(
    actividad_convenio_id: int,
    data: NoAplicaRequest,
    user: Dict[str, Any] = Depends(get_current_user_seguimiento),
):
    if user.get("rol") == "DIRECTORA":
        raise HTTPException(status_code=403, detail="El rol Directora no puede editar actividades")

    with engine_analitica.connect() as conn:
        prev = conn.execute(
            text("""
                SELECT estado, porcentaje_avance, convenio_id, actividad_base_id
                FROM actividades_convenio_seg_mc WHERE id=:id
            """),
            {"id": actividad_convenio_id},
        ).mappings().fetchone()
        if not prev:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")

        est_ant = prev["estado"] or "Pendiente"
        pct_ant = prev["porcentaje_avance"] or 0
        convenio_id = prev["convenio_id"]
        actividad_base_id = prev["actividad_base_id"]

        tipo_actividad = None
        if actividad_base_id is not None:
            fila_tipo = conn.execute(
                text("SELECT tipo FROM actividades_base_seg_mc WHERE id=:id"), {"id": actividad_base_id}
            ).mappings().fetchone()
            tipo_actividad = fila_tipo["tipo"] if fila_tipo else None

        if data.no_aplica:
            nuevo_estado, nuevo_pct = "Completada", 100
            fecha_completado = date.today()
            comentario = 'Marcada como "No aplica" (se contabiliza como completada).'
        else:
            nuevo_estado, nuevo_pct = "Pendiente", 0
            fecha_completado = None
            comentario = 'Se revirtió la marca de "No aplica".'

        conn.execute(
            text("""
                UPDATE actividades_convenio_seg_mc
                SET estado=:estado, porcentaje_avance=:pct, fecha_completado=:fecha_completado,
                    no_aplica=:no_aplica, responsable_id=:responsable_id, ultimo_comentario=:comentario
                WHERE id=:id
            """),
            {
                "estado": nuevo_estado, "pct": nuevo_pct, "fecha_completado": fecha_completado,
                "no_aplica": 1 if data.no_aplica else 0, "responsable_id": user["usuario_id"],
                "comentario": comentario, "id": actividad_convenio_id,
            },
        )
        conn.execute(
            text("""
                INSERT INTO historial_actividades_seg_mc
                    (actividad_convenio_id, usuario_id, usuario_nombre,
                     estado_anterior, estado_nuevo, porcentaje_anterior, porcentaje_nuevo, comentario)
                VALUES (:acid, :uid, :unombre, :est_ant, :est_nuevo, :pct_ant, :pct_nuevo, :comentario)
            """),
            {
                "acid": actividad_convenio_id, "uid": user["usuario_id"], "unombre": user["nombre"],
                "est_ant": est_ant, "est_nuevo": nuevo_estado, "pct_ant": pct_ant, "pct_nuevo": nuevo_pct,
                "comentario": comentario,
            },
        )

        if actividad_base_id == 22 and convenio_id is not None:
            conn.execute(
                text("UPDATE convenios_seg_proceso_mc SET fecha_firma_director_general=:f WHERE id=:cid"),
                {"f": fecha_completado, "cid": convenio_id},
            )

        conn.commit()

    if convenio_id is None:
        return AvanceResponse(avanzo_estado_convenio=False)
    return _verificar_avance_automatico_convenio(convenio_id, tipo_actividad)


@router.patch("/actividades/{actividad_convenio_id}/recordatorio", summary="Guardar/desactivar el recordatorio por correo de una actividad")
def update_recordatorio(
    actividad_convenio_id: int,
    data: RecordatorioUpdateRequest,
    user: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> Dict[str, Any]:
    if user.get("rol") == "DIRECTORA":
        raise HTTPException(status_code=403, detail="El rol Directora no puede editar actividades")

    with engine_analitica.connect() as conn:
        prev = conn.execute(
            text("SELECT fecha_recordatorio, nota_recordatorio FROM actividades_convenio_seg_mc WHERE id=:id"),
            {"id": actividad_convenio_id},
        ).mappings().fetchone()
        if prev is None:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")

        fecha_previa = prev["fecha_recordatorio"]
        nota_previa = prev["nota_recordatorio"]
        cambio = (data.fecha_recordatorio != fecha_previa) or (data.nota_recordatorio != nota_previa)

        if cambio:
            conn.execute(
                text("""
                    UPDATE actividades_convenio_seg_mc
                    SET fecha_recordatorio=:fecha, nota_recordatorio=:nota, recordatorio_enviado=0
                    WHERE id=:id
                """),
                {"fecha": data.fecha_recordatorio, "nota": data.nota_recordatorio, "id": actividad_convenio_id},
            )
        else:
            conn.execute(
                text("""
                    UPDATE actividades_convenio_seg_mc
                    SET fecha_recordatorio=:fecha, nota_recordatorio=:nota
                    WHERE id=:id
                """),
                {"fecha": data.fecha_recordatorio, "nota": data.nota_recordatorio, "id": actividad_convenio_id},
            )
        conn.commit()

    return {"actualizado": cambio}


@router.get("/convenios/{convenio_id}/historial", summary="Historial de comentarios de todos los períodos de un convenio")
def get_historial_convenio(
    convenio_id: int,
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> Dict[str, List[Dict[str, Any]]]:
    with engine_analitica.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT h.actividad_convenio_id, h.fecha_cambio, h.usuario_nombre, h.comentario
                FROM historial_actividades_seg_mc h
                JOIN actividades_convenio_seg_mc ac ON h.actividad_convenio_id = ac.id
                WHERE ac.convenio_id = :cid AND h.comentario IS NOT NULL AND h.comentario != ''
                ORDER BY h.actividad_convenio_id, h.fecha_cambio DESC
            """),
            {"cid": convenio_id},
        ).mappings().all()

    historial: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        key = str(r["actividad_convenio_id"])
        historial.setdefault(key, []).append({
            "fecha_cambio": r["fecha_cambio"],
            "usuario_nombre": r["usuario_nombre"],
            "comentario": r["comentario"],
        })
    return historial


@router.get("/periodos/{periodo_id}/historial", summary="Historial de comentarios de un período específico")
def get_historial_periodo(
    periodo_id: int,
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> Dict[str, List[Dict[str, Any]]]:
    with engine_analitica.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT h.actividad_convenio_id, h.fecha_cambio, h.usuario_nombre, h.comentario
                FROM historial_actividades_seg_mc h
                JOIN actividades_convenio_seg_mc ac ON h.actividad_convenio_id = ac.id
                WHERE ac.convenio_periodo_id = :pid AND h.comentario IS NOT NULL AND h.comentario != ''
                ORDER BY h.actividad_convenio_id, h.fecha_cambio DESC
            """),
            {"pid": periodo_id},
        ).mappings().all()

    historial: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        key = str(r["actividad_convenio_id"])
        historial.setdefault(key, []).append({
            "fecha_cambio": r["fecha_cambio"],
            "usuario_nombre": r["usuario_nombre"],
            "comentario": r["comentario"],
        })
    return historial
