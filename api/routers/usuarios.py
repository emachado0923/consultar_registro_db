from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..core.database import get_session_analitica
from ..models.usuarios import Usuario, UsuarioCreate, UsuarioUpdate
from .auth import get_current_user

SessionDep = Annotated[Session, Depends(get_session_analitica)]
router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("/", response_model=List[Usuario], summary="Listar todos los usuarios")
def list_usuarios(session: SessionDep):
    """
    Devuelve la lista completa de usuarios.
    """
    statement = select(Usuario)
    results = session.exec(statement).all()
    return results


@router.get("/{user_id}", response_model=Usuario, summary="Obtener usuario por id")
def get_usuario(user_id: int, session: SessionDep, _: Dict[str, Any] = Depends(get_current_user)):
    """
    Obtiene un usuario por su id.
    """
    user = session.get(Usuario, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.get("/by-username/{username}", response_model=Usuario, summary="Obtener usuario por username")
def get_usuario_by_username(username: str, session: SessionDep, _: Dict[str, Any] = Depends(get_current_user)):
    """
    Obtiene un usuario por su username (único).
    """
    statement = select(Usuario).where(Usuario.username == username)
    result = session.exec(statement).first()
    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return result


@router.post("/agregar", response_model=Usuario, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo usuario")
def create_usuario(
    data: UsuarioCreate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> Usuario:
    """
    Crea un nuevo usuario. Maneja IntegrityError si username ya existe.
    """
    # Podrías añadir aquí hashing si recibes password en claro; asume que ya envían password_hash y sal.
    new_user = Usuario.from_orm(data)
    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="El username ya existe.")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")


@router.put("/{user_id}", response_model=Usuario, summary="Actualizar usuario (reemplaza campos especificados)")
def update_usuario(
    user_id: int,
    data: UsuarioUpdate,
    session: SessionDep,
    user: Dict[str, Any] = Depends(get_current_user),
) -> Usuario:
    """
    Actualiza campos del usuario (parcialmente). No permite cambiar el username aquí.
    """
    db_user = session.get(Usuario, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Actualizar solo campos que vengan en el payload
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    try:
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Conflicto de integridad en la actualización.")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar usuario por id")
def delete_usuario(user_id: int, session: SessionDep, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Elimina el usuario indicado. Devuelve 204 en caso de éxito.
    """
    db_user = session.get(Usuario, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    try:
        session.delete(db_user)
        session.commit()
        return None
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")

