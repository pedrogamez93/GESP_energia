# app/api/v1/roles.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.roles import RoleDTO, RoleCreate, RoleUpdate, UserRolesDTO
from app.services.role_service import RoleService
from app.core import roles as R

router = APIRouter(prefix="/api/v1/roles", tags=["Roles"])
svc = RoleService()
DbDep = Annotated[Session, Depends(get_db)]

# --- Roles básicos ---
@router.get("", response_model=List[RoleDTO])
def list_roles(db: DbDep, q: str | None = Query(None)):
    return svc.list_roles(db, q)

@router.post("", response_model=RoleDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear rol")
def create_role(
    payload: RoleCreate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles(R.ADMIN))],
):
    return svc.create_role(db, payload.Name)

@router.put("/{role_id}", response_model=RoleDTO,
            summary="(ADMINISTRADOR) Renombrar rol")
def rename_role(
    role_id: str,
    payload: RoleUpdate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles(R.ADMIN))],
):
    return svc.rename_role(db, role_id, payload.Name)

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar rol")
def delete_role(
    role_id: str,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles(R.ADMIN))],
):
    svc.delete_role(db, role_id)
    return None

# --- User ↔ Roles ---
@router.get("/user/{user_id}", response_model=List[str],
            summary="(ADMINISTRADOR) Listar roles de un usuario")
def list_user_roles(
    user_id: str,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles(R.ADMIN))],
):
    return svc.list_user_roles(db, user_id)

@router.post("/user/{user_id}/add/{role_name}", response_model=List[str],
             summary="(ADMINISTRADOR) Agregar rol a usuario")
def add_role_to_user(
    user_id: str,
    role_name: str,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles(R.ADMIN))],
):
    return svc.add_user_role(db, user_id, role_name)

@router.delete("/user/{user_id}/remove/{role_name}", response_model=List[str],
               summary="(ADMINISTRADOR) Quitar rol de usuario")
def remove_role_from_user(
    user_id: str,
    role_name: str,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles(R.ADMIN))],
):
    return svc.remove_user_role(db, user_id, role_name)

@router.put("/user/{user_id}", response_model=List[str],
            summary="(ADMINISTRADOR) Reemplazar todos los roles de un usuario "
                    "(activa regla 1 tipo de gestor si quieres)")
def set_roles_for_user(
    user_id: str,
    payload: UserRolesDTO,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles(R.ADMIN))],
):
    return svc.set_user_roles(db, user_id, payload.Roles, enforce_single_gestor=False)

# --- Jerarquía / disponibles (igual a tu .NET) ---
@router.get("/assignable/current", response_model=List[RoleDTO],
            summary="Roles asignables por el usuario actual (propios + jerárquicos)")
def assignable_by_current(
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles(R.ADMIN))],
):
    roles = svc.assignable_roles_for_current_user(db, current_user.id)
    return [RoleDTO.model_validate(r) for r in roles]

@router.get("/user/{user_id}/available", response_model=List[RoleDTO],
            summary="Roles disponibles para asignar a un usuario (según jerarquía del usuario actual)")
def available_for_user(
    user_id: str,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles(R.ADMIN))],
):
    roles = svc.available_roles_for_user(db, user_id, current_user.id)
    return [RoleDTO.model_validate(r) for r in roles]

# --- Seed de roles canónicos ---
@router.post("/seed-defaults", response_model=List[str],
             summary="(ADMINISTRADOR) Crea los roles canónicos si faltan")
def seed_defaults(
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles(R.ADMIN))],
):
    return svc.seed_defaults(db)
