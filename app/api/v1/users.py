from __future__ import annotations

import logging
from typing import Literal, Union

from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import (
    UserCreate, UserUpdate, UserPatch, UserOut, ChangePassword
)
from app.services.user_service import (
    create_user, get_users, get_user_by_id, update_user, patch_user,
    soft_delete_user, toggle_active_user, change_password
)
from app.core.security import require_roles
from app.schemas.auth import UserPublic

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

DbDep = Depends(get_db)
Log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create(user: UserCreate, db: Session = DbDep):
    # Log de entrada (password enmascarado)
    data = user.model_dump()
    if "password" in data:
        data["password"] = "***"
    Log.info("[USERS_ROUTER] POST /users payload: %s", data)

    try:
        resp = create_user(db, user)
        Log.info("[USERS_ROUTER] Usuario creado OK (Id=%s)", getattr(resp, "Id", None))
        return resp
    except ValueError as e:
        Log.warning("[USERS_ROUTER] Error de negocio al crear usuario: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        Log.exception("[USERS_ROUTER] Error inesperado al crear usuario")
        raise HTTPException(
            status_code=500,
            detail="Error interno al crear usuario",
        ) from e


@router.get("", response_model=list[UserOut])
def read_users(
    db: Session = DbDep,
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(50, ge=1, le=200, description="Registros a devolver"),
    sort_by: str = Query("Id", description="Columna para ordenar"),
    sort_dir: str = Query("asc", pattern="^(?i)(asc|desc)$", description="Dirección de orden"),
    status: Literal["active", "inactive", "all"] = Query(
        "active", description="Filtrar por estado: active | inactive | all"
    ),
):
    return get_users(db, skip=skip, limit=limit, sort_by=sort_by, sort_dir=sort_dir, status=status)


@router.get("/{user_id}", response_model=UserOut)
def read_user_by_id(
    user_id: Union[int, str] = Path(..., description="Id del usuario"),
    db: Session = DbDep,
):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update(
    user_id: Union[int, str],
    payload: UserUpdate,
    db: Session = DbDep,
):
    try:
        return update_user(db, user_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{user_id}", response_model=UserOut)
def partial_update(
    user_id: Union[int, str],
    payload: UserPatch,
    db: Session = DbDep,
):
    try:
        return patch_user(db, user_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{user_id}/password", response_model=UserOut)
def update_password(
    user_id: Union[int, str],
    body: ChangePassword,
    db: Session = DbDep,
    current_user: UserPublic = Depends(require_roles("ADMINISTRADOR")),
):
    """
    Cambia la contraseña del usuario indicado.
    Restringido a ADMINISTRADORES.
    """
    try:
        return change_password(db, user_id, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{user_id}", response_model=UserOut, status_code=status.HTTP_200_OK)
def soft_delete(
    user_id: Union[int, str],
    db: Session = DbDep,
):
    try:
        return soft_delete_user(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{user_id}/restore", response_model=UserOut)
def restore_user(
    user_id: Union[int, str],
    db: Session = DbDep,
):
    try:
        return toggle_active_user(db, user_id, True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{user_id}/toggle", response_model=UserOut)
def toggle_active(
    user_id: Union[int, str],
    enable: bool = Query(..., description="true = activar, false = desactivar"),
    db: Session = DbDep,
):
    try:
        return toggle_active_user(db, user_id, enable)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/me/password", response_model=UserOut)
def self_update_password(
    body: ChangePassword,
    db: Session = DbDep,
    current_user: UserPublic = Depends(require_roles("ADMINISTRADOR", "USUARIO")),
):
    """El usuario autenticado cambia su propia contraseña."""
    return change_password(db, current_user.id, body.new_password)
