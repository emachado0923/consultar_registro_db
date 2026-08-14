from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlmodel import Session

from ..core.actividades_seguimiento import crear_instancias_actividades
from ..core.database import engine_analitica, get_session_analitica
from ..models.seguimiento_catalogo import ActividadBaseCreate, ActividadBaseUpdate
from .seguimiento_auth import get_current_user_seguimiento, require_rol

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/seguimiento/catalogo", tags=["Seguimiento · Catálogo de actividades"])

TIPOS_VALIDOS = ("ejecucion", "liquidacion", "cierre")


def _validar_tipo(tipo: str) -> None:
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"tipo debe ser uno de {TIPOS_VALIDOS}")


@router.get("/{tipo}", summary="Listar actividades del catálogo por tipo (ejecucion|liquidacion|cierre)")
def list_catalogo(
    tipo: str,
    _: Dict[str, Any] = Depends(get_current_user_seguimiento),
) -> List[Dict[str, Any]]:
    _validar_tipo(tipo)
    with engine_analitica.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, nombre, subcategoria, subcategoria_orden, orden, es_relevante, tiene_fecha_limite
                FROM actividades_base_seg_mc
                WHERE tipo = :tipo
                ORDER BY orden
            """),
            {"tipo": tipo},
        ).mappings().all()
    return [dict(r) for r in rows]


@router.post("/{tipo}", status_code=status.HTTP_201_CREATED, summary="Agregar actividad al catálogo (solo ADMIN)")
def create_actividad_catalogo(
    tipo: str,
    data: ActividadBaseCreate,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
) -> Dict[str, Any]:
    """
    Réplica exacta de app/seguimiento/db.py::agregar_actividad_catalogo: recorre
    (+1) el orden de las actividades del mismo tipo que ya estaban en esa
    posición o después, para insertar sin duplicar posiciones. No expone
    'aplica_a' (revertido en favor del botón manual "No aplica" por actividad).

    A diferencia del Streamlit original (que requería entrar convenio por
    convenio, período por período, y darle clic a "🔄 Sincronizar" en cada
    uno), acá la sincronización es automática: apenas se crea la actividad,
    se agrega como instancia "Pendiente" en TODOS los períodos existentes que
    ya tengan actividades de este tipo — sin ningún paso manual adicional.
    """
    _validar_tipo(tipo)
    if not data.nombre.strip() or not data.subcategoria.strip():
        raise HTTPException(status_code=400, detail="Nombre y subcategoría son obligatorios.")

    with engine_analitica.connect() as conn:
        conn.execute(
            text("UPDATE actividades_base_seg_mc SET orden = orden + 1 WHERE tipo = :tipo AND orden >= :orden"),
            {"tipo": tipo, "orden": data.orden},
        )
        result = conn.execute(
            text("""
                INSERT INTO actividades_base_seg_mc
                    (nombre, descripcion, tipo, subcategoria, subcategoria_orden,
                     orden, es_relevante, tiene_fecha_limite)
                VALUES (:nombre, NULL, :tipo, :subcategoria, :subcategoria_orden,
                        :orden, :es_relevante, :tiene_fecha_limite)
            """),
            {
                "nombre": data.nombre.strip(),
                "tipo": tipo,
                "subcategoria": data.subcategoria.strip(),
                "subcategoria_orden": data.subcategoria_orden,
                "orden": data.orden,
                "es_relevante": int(data.es_relevante),
                "tiene_fecha_limite": int(data.tiene_fecha_limite),
            },
        )
        conn.commit()
        nuevo_id = result.lastrowid

        periodos = conn.execute(
            text("SELECT id, convenio_id FROM convenio_periodos_seg_mc")
        ).mappings().all()

    periodos_sincronizados = 0
    for p in periodos:
        insertadas = crear_instancias_actividades(engine_analitica, p["convenio_id"], p["id"], tipo)
        if insertadas:
            periodos_sincronizados += 1

    return {"id": nuevo_id, "periodos_sincronizados": periodos_sincronizados, "total_periodos": len(periodos)}


@router.put("/{actividad_id}", summary="Editar actividad del catálogo, incl. reordenar (solo ADMIN)")
def update_actividad_catalogo(
    actividad_id: int,
    data: ActividadBaseUpdate,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
) -> Dict[str, Any]:
    """
    Réplica exacta de app/seguimiento/db.py::editar_actividad_catalogo: si el
    'orden' cambió, recorre las demás actividades del mismo tipo para no dejar
    huecos ni duplicados.
    """
    campos = data.dict(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")

    with engine_analitica.connect() as conn:
        actual = conn.execute(
            text("SELECT tipo, orden FROM actividades_base_seg_mc WHERE id=:aid"),
            {"aid": actividad_id},
        ).mappings().fetchone()
        if not actual:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")

        tipo = actual["tipo"]
        orden_actual = actual["orden"]
        nuevo_orden = campos.get("orden", orden_actual)

        if nuevo_orden != orden_actual:
            if nuevo_orden > orden_actual:
                conn.execute(
                    text("""
                        UPDATE actividades_base_seg_mc
                        SET orden = orden - 1
                        WHERE tipo = :tipo AND orden > :orden_actual AND orden <= :nuevo_orden AND id != :aid
                    """),
                    {"tipo": tipo, "orden_actual": orden_actual, "nuevo_orden": nuevo_orden, "aid": actividad_id},
                )
            else:
                conn.execute(
                    text("""
                        UPDATE actividades_base_seg_mc
                        SET orden = orden + 1
                        WHERE tipo = :tipo AND orden >= :nuevo_orden AND orden < :orden_actual AND id != :aid
                    """),
                    {"tipo": tipo, "orden_actual": orden_actual, "nuevo_orden": nuevo_orden, "aid": actividad_id},
                )

        if "es_relevante" in campos:
            campos["es_relevante"] = int(campos["es_relevante"])
        if "tiene_fecha_limite" in campos:
            campos["tiene_fecha_limite"] = int(campos["tiene_fecha_limite"])

        set_clause = ", ".join(f"{campo}=:{campo}" for campo in campos)
        conn.execute(
            text(f"UPDATE actividades_base_seg_mc SET {set_clause} WHERE id=:aid"),
            {**campos, "aid": actividad_id},
        )
        conn.commit()

    return {"id": actividad_id}


@router.delete("/{actividad_id}", summary="Eliminar actividad del catálogo y su avance en todos los convenios (solo ADMIN)")
def delete_actividad_catalogo(
    actividad_id: int,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
) -> Dict[str, Any]:
    with engine_analitica.connect() as conn:
        existe = conn.execute(
            text("SELECT id FROM actividades_base_seg_mc WHERE id=:aid"), {"aid": actividad_id}
        ).fetchone()
        if not existe:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")
        conn.execute(text("DELETE FROM actividades_convenio_seg_mc WHERE actividad_base_id=:aid"), {"aid": actividad_id})
        conn.execute(text("DELETE FROM actividades_base_seg_mc WHERE id=:aid"), {"aid": actividad_id})
        conn.commit()
    return {"status": "ok"}
