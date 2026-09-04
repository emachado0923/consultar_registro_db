from datetime import date
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from ..core.actividades_seguimiento import (
    calcular_nivel_alerta_convenio,
    crear_instancias_actividades,
    preseed_notificaciones_pasadas,
)
from ..core.database import engine_analitica, get_session_analitica
from ..core.fechas_seguimiento import calcular_fechas_liquidacion
from ..core.informes_seguimiento import _get_progreso_periodo
from ..models.seguimiento_alertas import ConvenioDetalleOut
from ..models.seguimiento_convenios import (
    ConvenioPeriodoCreate,
    ConvenioSeguimientoCreate,
    ConvenioSeguimientoUpdate,
)
from .seguimiento_auth import get_current_user_seguimiento, require_rol

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/seguimiento", tags=["Seguimiento · Convenios"])

ESTADOS_VALIDOS = ["En ejecución", "En liquidación", "En cierre", "Cerrado"]

# Réplica exacta de ESTADO_A_TIPO_ACTIVO en app/seguimiento/ui.py (Streamlit
# original) — determina qué etapa (tipo de actividad) está "activa" según el
# estado actual del convenio, para saber de qué tipo calcular el progreso.
ESTADO_A_TIPO_ACTIVO = {
    "En ejecución": "ejecucion",
    "En liquidación": "liquidacion",
    "En cierre": "cierre",
    "Cerrado": "cierre",
}


def _agregar_periodo_convenio(convenio_id: int, periodo: str) -> Optional[int]:
    """
    Réplica exacta de app/seguimiento/db.py::agregar_periodo_convenio.
    Crea el período (si no existía ya, comparando sin distinguir mayúsculas/espacios)
    y sus instancias de actividades para los 3 tipos. Retorna el id del período
    creado, o None si ya existía.
    """
    periodo = periodo.strip()
    with engine_analitica.connect() as conn:
        existentes = conn.execute(
            text("SELECT id, periodo, orden FROM convenio_periodos_seg_mc WHERE convenio_id=:cid ORDER BY orden, id"),
            {"cid": convenio_id},
        ).fetchall()
        if any(p.periodo.strip().lower() == periodo.lower() for p in existentes):
            return None
        nuevo_orden = (max((p.orden for p in existentes), default=0)) + 1
        result = conn.execute(
            text("INSERT INTO convenio_periodos_seg_mc (convenio_id, periodo, orden) VALUES (:cid, :periodo, :orden)"),
            {"cid": convenio_id, "periodo": periodo, "orden": nuevo_orden},
        )
        conn.commit()
        nuevo_id = result.lastrowid

    if nuevo_id:
        for tipo in ("ejecucion", "liquidacion", "cierre"):
            crear_instancias_actividades(engine_analitica, convenio_id, nuevo_id, tipo)
    return nuevo_id


@router.get("/convenios", summary="Listar convenios (con datos de la IES y nivel de alerta)")
def list_convenios(
    session: SessionDep,
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> List[Dict[str, Any]]:
    rows = session.exec(
        text("""
            SELECT c.id, c.codigo, i.nombre AS ies_nombre, i.sigla AS ies_sigla,
                   c.periodo_academico, c.estado, c.valor, c.adiciones_recursos,
                   c.fecha_limite_liquidacion_voluntaria, c.fecha_limite_liquidacion_unilateral,
                   c.fecha_limite_liquidacion_judicial, c.fecha_vencimiento_poliza,
                   c.supervisor, c.apoyo_supervision, c.fecha_firma_director_general
            FROM convenios_seg_proceso_mc c
            JOIN ies_seg_proceso_mc i ON c.ies_id = i.id
            ORDER BY c.estado, c.codigo
        """)
    ).mappings().all()

    resultado = []
    for r in rows:
        d = dict(r)
        # Igual que en pagina_tablero() del Streamlit original: cada tarjeta de
        # convenio se colorea según su nivel de alerta más urgente vigente.
        nivel_alerta, motivos_alerta = calcular_nivel_alerta_convenio(
            engine_analitica,
            d["id"],
            d["fecha_limite_liquidacion_voluntaria"],
            d["fecha_limite_liquidacion_unilateral"],
            d["fecha_limite_liquidacion_judicial"],
            d["fecha_vencimiento_poliza"],
            d["fecha_firma_director_general"],
            d["estado"],
        )
        d["nivel_alerta"] = nivel_alerta
        d["motivos_alerta"] = motivos_alerta
        resultado.append(d)
    return resultado


@router.post("/convenios", status_code=status.HTTP_201_CREATED, summary="Registrar nuevo convenio (solo ADMIN)")
def create_convenio(
    data: ConvenioSeguimientoCreate,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
) -> Dict[str, Any]:
    f_liq_vol, f_liq_uni, f_liq_jud = calcular_fechas_liquidacion(data.fecha_fin_convenio)

    with engine_analitica.connect() as conn:
        try:
            result = conn.execute(
                text("""
                    INSERT INTO convenios_seg_proceso_mc
                        (codigo, ies_id, periodo_academico, estado, valor,
                         fecha_inicio_convenio, fecha_fin_convenio,
                         fecha_limite_liquidacion_voluntaria, fecha_limite_liquidacion_unilateral,
                         fecha_limite_liquidacion_judicial, fecha_vencimiento_poliza,
                         supervisor, apoyo_supervision, observaciones_generales, creado_por)
                    VALUES (:codigo, :ies_id, :periodo_academico, 'En ejecución', :valor,
                            :fecha_inicio_convenio, :fecha_fin_convenio,
                            :f_liq_vol, :f_liq_uni, :f_liq_jud, :fecha_vencimiento_poliza,
                            :supervisor, :apoyo_supervision, :observaciones_generales, :creado_por)
                """),
                {
                    "codigo": data.codigo.strip(),
                    "ies_id": data.ies_id,
                    "periodo_academico": data.periodo_academico.strip(),
                    "valor": data.valor,
                    "fecha_inicio_convenio": data.fecha_inicio_convenio,
                    "fecha_fin_convenio": data.fecha_fin_convenio,
                    "f_liq_vol": f_liq_vol,
                    "f_liq_uni": f_liq_uni,
                    "f_liq_jud": f_liq_jud,
                    "fecha_vencimiento_poliza": data.fecha_vencimiento_poliza,
                    "supervisor": data.supervisor,
                    "apoyo_supervision": data.apoyo_supervision,
                    "observaciones_generales": data.observaciones_generales,
                    "creado_por": data.creado_por,
                },
            )
            conn.commit()
            new_id = result.lastrowid
        except IntegrityError:
            raise HTTPException(status_code=400, detail="Ya existe un convenio con ese código.")

    if not new_id:
        raise HTTPException(status_code=500, detail="No se pudo crear el convenio.")

    _agregar_periodo_convenio(new_id, data.periodo_academico)
    preseed_notificaciones_pasadas(engine_analitica, new_id, f_liq_vol, f_liq_uni, f_liq_jud, data.fecha_vencimiento_poliza)

    return {
        "id": new_id,
        "codigo": data.codigo.strip(),
        "fecha_limite_liquidacion_voluntaria": f_liq_vol,
        "fecha_limite_liquidacion_unilateral": f_liq_uni,
        "fecha_limite_liquidacion_judicial": f_liq_jud,
    }


@router.get("/convenios/{convenio_id}", response_model=ConvenioDetalleOut, summary="Detalle de un convenio, con nivel de alerta")
def get_convenio_detalle(
    convenio_id: int,
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> ConvenioDetalleOut:
    with engine_analitica.connect() as conn:
        row = conn.execute(
            text("""
                SELECT c.id, c.codigo, i.nombre AS ies_nombre, i.sigla AS ies_sigla,
                       c.periodo_academico, c.estado, c.valor, c.adiciones_recursos,
                       c.fecha_inicio_convenio, c.fecha_fin_convenio,
                       c.fecha_limite_liquidacion_voluntaria, c.fecha_limite_liquidacion_unilateral,
                       c.fecha_limite_liquidacion_judicial, c.fecha_vencimiento_poliza,
                       c.supervisor, c.apoyo_supervision, c.observaciones_generales,
                       c.fecha_firma_director_general, c.creado_por
                FROM convenios_seg_proceso_mc c
                JOIN ies_seg_proceso_mc i ON c.ies_id = i.id
                WHERE c.id = :cid
            """),
            {"cid": convenio_id},
        ).mappings().fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Convenio no encontrado")

    nivel_alerta, motivos_alerta = calcular_nivel_alerta_convenio(
        engine_analitica,
        convenio_id,
        row["fecha_limite_liquidacion_voluntaria"],
        row["fecha_limite_liquidacion_unilateral"],
        row["fecha_limite_liquidacion_judicial"],
        row["fecha_vencimiento_poliza"],
        row["fecha_firma_director_general"],
        row["estado"],
    )

    return ConvenioDetalleOut(
        id=row["id"],
        codigo=row["codigo"],
        ies_nombre=row["ies_nombre"],
        ies_sigla=row["ies_sigla"],
        periodo_academico=row["periodo_academico"],
        estado=row["estado"],
        valor=float(row["valor"]) if row["valor"] is not None else None,
        adiciones_recursos=float(row["adiciones_recursos"]) if row["adiciones_recursos"] is not None else None,
        fecha_inicio_convenio=str(row["fecha_inicio_convenio"]) if row["fecha_inicio_convenio"] else None,
        fecha_fin_convenio=str(row["fecha_fin_convenio"]) if row["fecha_fin_convenio"] else None,
        fecha_limite_liquidacion_voluntaria=str(row["fecha_limite_liquidacion_voluntaria"]) if row["fecha_limite_liquidacion_voluntaria"] else None,
        fecha_limite_liquidacion_unilateral=str(row["fecha_limite_liquidacion_unilateral"]) if row["fecha_limite_liquidacion_unilateral"] else None,
        fecha_limite_liquidacion_judicial=str(row["fecha_limite_liquidacion_judicial"]) if row["fecha_limite_liquidacion_judicial"] else None,
        fecha_vencimiento_poliza=str(row["fecha_vencimiento_poliza"]) if row["fecha_vencimiento_poliza"] else None,
        fecha_firma_director_general=str(row["fecha_firma_director_general"]) if row["fecha_firma_director_general"] else None,
        supervisor=row["supervisor"],
        apoyo_supervision=row["apoyo_supervision"],
        observaciones_generales=row["observaciones_generales"],
        creado_por=row["creado_por"],
        nivel_alerta=nivel_alerta,
        motivos_alerta=motivos_alerta,
    )


@router.put("/convenios/{convenio_id}", summary="Editar un convenio (solo ADMIN)")
def update_convenio(
    convenio_id: int,
    data: ConvenioSeguimientoUpdate,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
) -> Dict[str, Any]:
    campos = data.dict(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")

    with engine_analitica.connect() as conn:
        actual = conn.execute(
            text("SELECT fecha_fin_convenio, fecha_vencimiento_poliza FROM convenios_seg_proceso_mc WHERE id=:cid"),
            {"cid": convenio_id},
        ).mappings().fetchone()
        if not actual:
            raise HTTPException(status_code=404, detail="Convenio no encontrado")

        nueva_fecha_fin = campos.get("fecha_fin_convenio", actual["fecha_fin_convenio"])
        nueva_fecha_pol = campos.get("fecha_vencimiento_poliza", actual["fecha_vencimiento_poliza"])
        f_liq_vol, f_liq_uni, f_liq_jud = calcular_fechas_liquidacion(nueva_fecha_fin)
        campos["fecha_limite_liquidacion_voluntaria"] = f_liq_vol
        campos["fecha_limite_liquidacion_unilateral"] = f_liq_uni
        campos["fecha_limite_liquidacion_judicial"] = f_liq_jud

        set_clause = ", ".join(f"{campo}=:{campo}" for campo in campos)
        try:
            conn.execute(
                text(f"UPDATE convenios_seg_proceso_mc SET {set_clause} WHERE id=:cid"),
                {**campos, "cid": convenio_id},
            )
            conn.commit()
        except IntegrityError:
            raise HTTPException(status_code=400, detail="Ya existe un convenio con ese código.")

    preseed_notificaciones_pasadas(engine_analitica, convenio_id, f_liq_vol, f_liq_uni, f_liq_jud, nueva_fecha_pol)

    return {
        "id": convenio_id,
        "fecha_limite_liquidacion_voluntaria": f_liq_vol,
        "fecha_limite_liquidacion_unilateral": f_liq_uni,
        "fecha_limite_liquidacion_judicial": f_liq_jud,
    }


@router.get("/convenios/{convenio_id}/periodos", summary="Listar períodos de un convenio, con su % de avance en la etapa activa")
def list_periodos(
    convenio_id: int,
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> List[Dict[str, Any]]:
    with engine_analitica.connect() as conn:
        estado = conn.execute(
            text("SELECT estado FROM convenios_seg_proceso_mc WHERE id=:cid"), {"cid": convenio_id}
        ).scalar()
        rows = conn.execute(
            text("SELECT id, convenio_id, periodo, orden, creado_en FROM convenio_periodos_seg_mc WHERE convenio_id=:cid ORDER BY orden, id"),
            {"cid": convenio_id},
        ).mappings().all()

    # Igual que en pagina_tablero() del Streamlit original: cada período
    # muestra su barra de progreso calculada sobre la etapa (tipo) activa
    # según el estado actual del convenio, no sobre las 3 etapas a la vez.
    tipo_activo = ESTADO_A_TIPO_ACTIVO.get(estado, "liquidacion")
    resultado = []
    for r in rows:
        d = dict(r)
        d["porcentaje_avance"] = _get_progreso_periodo(engine_analitica, d["id"], tipo_activo)
        resultado.append(d)
    return resultado


@router.post("/convenios/{convenio_id}/periodos", status_code=status.HTTP_201_CREATED, summary="Agregar un período a un convenio (solo ADMIN)")
def create_periodo(
    convenio_id: int,
    data: ConvenioPeriodoCreate,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
) -> Dict[str, Any]:
    with engine_analitica.connect() as conn:
        existe = conn.execute(
            text("SELECT id FROM convenios_seg_proceso_mc WHERE id=:cid"), {"cid": convenio_id}
        ).fetchone()
    if not existe:
        raise HTTPException(status_code=404, detail="Convenio no encontrado")

    nuevo_id = _agregar_periodo_convenio(convenio_id, data.periodo)
    if not nuevo_id:
        raise HTTPException(status_code=400, detail="Ese período ya existe para este convenio.")
    return {"id": nuevo_id, "convenio_id": convenio_id, "periodo": data.periodo.strip()}


@router.delete("/periodos/{periodo_id}", summary="Eliminar un período (y su avance) de un convenio (solo ADMIN)")
def delete_periodo(
    periodo_id: int,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
) -> Dict[str, Any]:
    with engine_analitica.connect() as conn:
        existe = conn.execute(
            text("SELECT id FROM convenio_periodos_seg_mc WHERE id=:pid"), {"pid": periodo_id}
        ).fetchone()
        if not existe:
            raise HTTPException(status_code=404, detail="Período no encontrado")
        # ON DELETE CASCADE en actividades_convenio_seg_mc / historial se encarga del resto.
        conn.execute(text("DELETE FROM convenio_periodos_seg_mc WHERE id=:pid"), {"pid": periodo_id})
        conn.commit()
    return {"status": "ok"}
