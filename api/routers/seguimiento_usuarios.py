from typing import Any, Dict, List
 
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
 
from ..core.database import engine_analitica
from ..core.security_seguimiento import hash_password
from ..models.seguimiento_usuarios import (
    UsuarioSeguimientoCreate,
    UsuarioSeguimientoEstadoUpdate,
    UsuarioSeguimientoPasswordUpdate,
    UsuarioSeguimientoPublic,
)
from .seguimiento_auth import require_rol
 
router = APIRouter(prefix="/seguimiento/usuarios", tags=["Seguimiento · Usuarios"])
 
ROLES_VALIDOS = ("ADMIN", "DIRECTORA", "LMC", "AST", "AD", "AF", "AJ")
 
 
@router.get("/", response_model=List[UsuarioSeguimientoPublic], summary="Listar usuarios de Seguimiento (solo ADMIN)")
def list_usuarios(_: Dict[str, Any] = Depends(require_rol("ADMIN"))):
    with engine_analitica.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, nombre, usuario, rol, activo, primer_login, creado_en
                FROM usuarios_seg_proceso_mc
                ORDER BY rol, nombre
            """)
        ).mappings().all()
    return [dict(r) for r in rows]
 
 
@router.post("/", response_model=UsuarioSeguimientoPublic, status_code=status.HTTP_201_CREATED, summary="Crear usuario de Seguimiento (solo ADMIN)")
def create_usuario(
    data: UsuarioSeguimientoCreate,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
):
    if data.rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail=f"rol debe ser uno de {ROLES_VALIDOS}")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres.")
    if not data.nombre.strip() or not data.usuario.strip():
        raise HTTPException(status_code=400, detail="Nombre y usuario son obligatorios.")
 
    pwd_hash = hash_password(data.password)
    with engine_analitica.connect() as conn:
        existe = conn.execute(
            text("SELECT id FROM usuarios_seg_proceso_mc WHERE usuario=:u"), {"u": data.usuario.strip()}
        ).fetchone()
        if existe:
            raise HTTPException(status_code=400, detail="Ya existe un usuario con ese nombre de usuario.")
        result = conn.execute(
            text("""
                INSERT INTO usuarios_seg_proceso_mc (nombre, usuario, password_hash, rol, primer_login)
                VALUES (:nombre, :usuario, :password_hash, :rol, 1)
            """),
            {
                "nombre": data.nombre.strip(),
                "usuario": data.usuario.strip(),
                "password_hash": pwd_hash,
                "rol": data.rol,
            },
        )
        conn.commit()
        nuevo_id = result.lastrowid
 
        row = conn.execute(
            text("""
                SELECT id, nombre, usuario, rol, activo, primer_login, creado_en
                FROM usuarios_seg_proceso_mc WHERE id=:id
            """),
            {"id": nuevo_id},
        ).mappings().fetchone()
    return dict(row)
 
 
@router.patch("/{usuario_id}/estado", response_model=UsuarioSeguimientoPublic, summary="Activar/desactivar un usuario (solo ADMIN)")
def update_estado_usuario(
    usuario_id: int,
    data: UsuarioSeguimientoEstadoUpdate,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
):
    if data.activo not in (0, 1):
        raise HTTPException(status_code=400, detail="activo debe ser 0 o 1")
    with engine_analitica.connect() as conn:
        existe = conn.execute(
            text("SELECT id FROM usuarios_seg_proceso_mc WHERE id=:id"), {"id": usuario_id}
        ).fetchone()
        if not existe:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        conn.execute(
            text("UPDATE usuarios_seg_proceso_mc SET activo=:activo WHERE id=:id"),
            {"activo": data.activo, "id": usuario_id},
        )
        conn.commit()
        row = conn.execute(
            text("""
                SELECT id, nombre, usuario, rol, activo, primer_login, creado_en
                FROM usuarios_seg_proceso_mc WHERE id=:id
            """),
            {"id": usuario_id},
        ).mappings().fetchone()
    return dict(row)
 
 
@router.patch("/{usuario_id}/password", summary="Restablecer la contraseña de un usuario (solo ADMIN)")
def reset_password_usuario(
    usuario_id: int,
    data: UsuarioSeguimientoPasswordUpdate,
    _: Dict[str, Any] = Depends(require_rol("ADMIN")),
):
    """
    Reseteo de contraseña hecho por un administrador (p. ej. el usuario la
    olvidó). Distinto de /seguimiento/auth/cambiar-password, que es el
    propio usuario cambiando SU contraseña en el primer login. Al resetearla
    acá se vuelve a marcar primer_login=1, para que el usuario esté obligado
    a poner una contraseña propia (que el admin no conozca) en su próximo
    ingreso.
    """
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres.")
 
    pwd_hash = hash_password(data.password)
    with engine_analitica.connect() as conn:
        existe = conn.execute(
            text("SELECT id FROM usuarios_seg_proceso_mc WHERE id=:id"), {"id": usuario_id}
        ).fetchone()
        if not existe:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        conn.execute(
            text("UPDATE usuarios_seg_proceso_mc SET password_hash=:h, primer_login=1 WHERE id=:id"),
            {"h": pwd_hash, "id": usuario_id},
        )
        conn.commit()
    return {"status": "ok"}
 
 
@router.delete("/{usuario_id}", summary="Eliminar un usuario (solo ADMIN)")
def delete_usuario(
    usuario_id: int,
    user: Dict[str, Any] = Depends(require_rol("ADMIN")),
):
    """
    Elimina el registro por completo (no es lo mismo que desactivar). Un
    usuario que ya haya reportado avance o quedado como responsable de
    alguna actividad tiene filas en actividades_convenio_seg_mc y/o
    historial_actividades_seg_mc que apuntan a su id — el FOREIGN KEY de
    esas tablas bloquea el DELETE en ese caso (por diseño: no queremos
    perder el rastro de quién hizo qué). Para esos usuarios, la opción es
    desactivarlos (botón "Desactivar"), no eliminarlos.
    """
    if user.get("usuario_id") == usuario_id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario mientras tienes la sesión iniciada con él.")
 
    with engine_analitica.connect() as conn:
        existe = conn.execute(
            text("SELECT id FROM usuarios_seg_proceso_mc WHERE id=:id"), {"id": usuario_id}
        ).fetchone()
        if not existe:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        try:
            conn.execute(text("DELETE FROM usuarios_seg_proceso_mc WHERE id=:id"), {"id": usuario_id})
            conn.commit()
        except IntegrityError:
            conn.rollback()
            raise HTTPException(
                status_code=409,
                detail=(
                    "No se puede eliminar: este usuario ya tiene actividades o historial "
                    "asociados en el sistema. Desactívalo en su lugar (botón \"Desactivar\")."
                ),
            )
    return {"status": "eliminado"}