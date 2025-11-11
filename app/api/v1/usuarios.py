# app/api/v1/usuarios.py
from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Body, Depends, Path, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.usuario_vinculo import IdsPayload, UserDetailFullDTO
from app.services.usuario_vinculo_service import UsuarioVinculoService
from app.db.models.identity import AspNetUser

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios (admin)"])
svc = UsuarioVinculoService()
DbDep = Annotated[Session, Depends(get_db)]


def _actor_id(current_user: UserPublic | None, request: Request | None) -> Optional[str]:
    # Prioriza usuario autenticado; si no, permite header X-User-Id (igual que en divisiones)
    return (current_user.id if current_user else None) or (
        request.headers.get("X-User-Id") if request else None
    )


def _to_full_dto(
    user: AspNetUser,
    roles: list[str],
    inst_ids: list[int],
    srv_ids: list[int],
    div_ids: list[int],
    uni_ids: list[int],
) -> UserDetailFullDTO:
    """
    Mapea directamente todas las columnas del modelo AspNetUser (from_attributes=True)
    y 'inyecta' roles y sets vinculados.
    Importante: asegúrate de que UserDetailFullDTO tenga tipos reales (bool/int/datetime)
    para evitar ValidationError.
    """
    base = UserDetailFullDTO.model_validate(user)  # toma todos los campos del modelo
    base.Roles = roles or []
    base.InstitucionIds = inst_ids or []
    base.ServicioIds = srv_ids or []
    base.DivisionIds = div_ids or []
    base.UnidadIds = uni_ids or []
    return base


# ---------------- Alias / Ping (evita 404 en GET /api/v1/usuarios) ----------------
@router.get(
    "",
    summary="Alias/ping del router admin de usuarios",
    description=(
        "Compatibilidad: evita 404 en GET /api/v1/usuarios. "
        "Para listar usuarios usa /api/v1/users. "
        "Este router expone endpoints administrativos de detalle y vinculación."
    ),
)
def usuarios_index(
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return {
        "status": "ok",
        "hint": "Usa /api/v1/users para listar usuarios",
        "endpoints": {
            "detalle": "/api/v1/usuarios/{user_id}",
            "instituciones": "/api/v1/usuarios/{user_id}/instituciones",
            "servicios": "/api/v1/usuarios/{user_id}/servicios",
            "divisiones": "/api/v1/usuarios/{user_id}/divisiones",
            "unidades": "/api/v1/usuarios/{user_id}/unidades",
            "activar": "/api/v1/usuarios/{user_id}/activar",
            "desactivar": "/api/v1/usuarios/{user_id}/desactivar",
        },
    }


# ---------------- Detalle admin ----------------
@router.get(
    "/{user_id}",
    summary="Detalle de usuario (ADMIN): roles, sets vinculados y todas las columnas de AspNetUsers",
    response_model=UserDetailFullDTO,
)
def get_user_detail(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    user, roles, inst_ids, srv_ids, div_ids, uni_ids = svc.get_detail(db, user_id)
    return _to_full_dto(user, roles, inst_ids, srv_ids, div_ids, uni_ids)


# ---------------- Reemplazar sets vinculados (ADMIN) ----------------
@router.put(
    "/{user_id}/instituciones",
    response_model=List[int],
    summary="(ADMIN) Reemplaza instituciones vinculadas",
)
def set_user_instituciones(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
    payload: Annotated[IdsPayload | None, Body(None)] = None,
):
    ids = payload.Ids if payload else []
    return svc.set_instituciones(db, user_id, ids)


@router.put(
    "/{user_id}/servicios",
    response_model=List[int],
    summary="(ADMIN) Reemplaza servicios vinculados",
)
def set_user_servicios(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
    payload: Annotated[IdsPayload | None, Body(None)] = None,
):
    ids = payload.Ids if payload else []
    return svc.set_servicios(db, user_id, ids)


@router.put(
    "/{user_id}/divisiones",
    response_model=List[int],
    summary="(ADMIN) Reemplaza divisiones vinculadas",
)
def set_user_divisiones(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
    payload: Annotated[IdsPayload | None, Body(None)] = None,
):
    ids = payload.Ids if payload else []
    return svc.set_divisiones(db, user_id, ids)


@router.put(
    "/{user_id}/unidades",
    response_model=List[int],
    summary="(ADMIN) Reemplaza unidades vinculadas",
)
def set_user_unidades(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
    payload: Annotated[IdsPayload | None, Body(None)] = None,
):
    ids = payload.Ids if payload else []
    return svc.set_unidades(db, user_id, ids)


@router.put(
    "/{user_id}/activar",
    response_model=UserDetailFullDTO,
    summary="(ADMIN) Activar usuario (Active = true)",
)
def activar_usuario(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    request: Request,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.set_active(db, user_id, True, actor_id=_actor_id(current_user, request))
    user, roles, inst_ids, srv_ids, div_ids, uni_ids = svc.get_detail(db, user_id)
    return _to_full_dto(user, roles, inst_ids, srv_ids, div_ids, uni_ids)


@router.put(
    "/{user_id}/desactivar",
    response_model=UserDetailFullDTO,
    summary="(ADMIN) Desactivar usuario (Active = false)",
)
def desactivar_usuario(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    request: Request,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.set_active(db, user_id, False, actor_id=_actor_id(current_user, request))
    user, roles, inst_ids, srv_ids, div_ids, uni_ids = svc.get_detail(db, user_id)
    return _to_full_dto(user, roles, inst_ids, srv_ids, div_ids, uni_ids)
