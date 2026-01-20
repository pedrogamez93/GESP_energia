from __future__ import annotations

import logging
from typing import Annotated, List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Request, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.unidad import UnidadSelectDTO
from app.schemas.usuario_vinculo import (
    IdsPayload,
    UserDetailFullDTO,
    UserMiniDTO,
)
from app.schemas.usuario_roles import RolesPayload

from app.services.usuario_vinculo_service import UsuarioVinculoService
from app.db.models.identity import AspNetUser
from app.db.models.usuarios_unidades import UsuarioUnidad

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios (admin)"])
svc = UsuarioVinculoService()
DbDep = Annotated[Session, Depends(get_db)]
Log = logging.getLogger(__name__)

# ==========================================================
# Roles (ajusta nombres EXACTOS a tu BD/JWT)
# ==========================================================
ROLE_ADMIN = "ADMINISTRADOR"
ROLE_GESTOR_SERVICIO = "GESTOR_SERVICIO"
ROLE_GESTOR_CONSULTA = "GESTOR DE CONSULTA"

USUARIOS_READ_ROLES = (ROLE_ADMIN, ROLE_GESTOR_SERVICIO, ROLE_GESTOR_CONSULTA)
USUARIOS_WRITE_ROLES = (ROLE_ADMIN, ROLE_GESTOR_SERVICIO)
USUARIOS_ADMIN_ONLY = (ROLE_ADMIN,)


def _actor_id(current_user: UserPublic | None, request: Request | None) -> Optional[str]:
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
    base = UserDetailFullDTO.model_validate(user)
    base.Roles = roles or []
    base.InstitucionIds = inst_ids or []
    base.ServicioIds = srv_ids or []
    base.DivisionIds = div_ids or []
    base.UnidadIds = uni_ids or []
    return base


def _assert_can_read_user_detail(actor: UserPublic, target_user_id: str) -> None:
    if ROLE_ADMIN in (actor.roles or []):
        return
    # el scope real lo impone el service (joins scoped)
    return


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
    _user: Annotated[UserPublic, Depends(require_roles(*USUARIOS_READ_ROLES))],
):
    return {
        "status": "ok",
        "hint": "Usa /api/v1/users para listar usuarios",
        "endpoints": {
            "detalle": "/api/v1/usuarios/{user_id} (READ: ADMIN/GESTOR_SERVICIOS/GESTOR DE CONSULTA, SCOPED)",
            "instituciones": "/api/v1/usuarios/{user_id}/instituciones (WRITE: ADMIN/GESTOR_SERVICIOS, SCOPED)",
            "servicios": "/api/v1/usuarios/{user_id}/servicios (WRITE: ADMIN/GESTOR_SERVICIOS, SCOPED)",
            "divisiones": "/api/v1/usuarios/{user_id}/divisiones (ADMIN)",
            "unidades": "/api/v1/usuarios/{user_id}/unidades (READ scoped) + PUT (WRITE scoped)",
            "roles": "/api/v1/usuarios/{user_id}/roles (ADMIN)",
            "activar": "/api/v1/usuarios/{user_id}/activar (ADMIN)",
            "desactivar": "/api/v1/usuarios/{user_id}/desactivar (ADMIN)",
        },
    }


# ==========================================================
# DEBUG: ver lo que el backend ve en UsuariosUnidades
# ==========================================================
@router.get("/{user_id}/debug-unidades")
def debug_unidades_usuario(
    user_id: Annotated[str, Path(...)],
    request_id: Annotated[Optional[str], Query()] = None,
    db: DbDep = None,
    current_user: Annotated[UserPublic, Depends(require_roles(*USUARIOS_READ_ROLES))] = None,
):
    """
    Debug controlado (requiere login). `user_id` es GUID string en Identity.
    """
    try:
        rows = db.execute(
            select(UsuarioUnidad.UsuarioId, UsuarioUnidad.UnidadId)
            .where(UsuarioUnidad.UsuarioId == user_id)
        ).all()
        Log.info("DEBUG-unidades user_id=%s request_id=%s rows=%s", user_id, request_id, rows)
        return [{"UsuarioId": r[0], "UnidadId": r[1]} for r in rows]
    except Exception as e:
        Log.exception("Error debug_unidades_usuario user_id=%s", user_id)
        raise HTTPException(status_code=500, detail="Error interno debug-unidades") from e


# ---------------- Detalle (READ scoped) ----------------
@router.get(
    "/{user_id}",
    summary="Detalle de usuario (roles, sets vinculados y columnas de AspNetUsers) (scoped)",
    response_model=UserDetailFullDTO,
)
def get_user_detail(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles(*USUARIOS_READ_ROLES))],
):
    _assert_can_read_user_detail(current_user, user_id)

    try:
        user, roles, inst_ids, srv_ids, div_ids, uni_ids = svc.get_detail_scoped(
            db, user_id, actor=current_user
        )
        Log.info(
            "GET detalle usuario %s actor=%s roles=%s -> inst=%s srv=%s div=%s uni=%s",
            user_id,
            getattr(current_user, "id", None),
            getattr(current_user, "roles", None),
            inst_ids, srv_ids, div_ids, uni_ids,
        )
        return _to_full_dto(user, roles, inst_ids, srv_ids, div_ids, uni_ids)
    except HTTPException:
        raise
    except Exception as e:
        Log.exception("Error get_user_detail user_id=%s actor=%s", user_id, getattr(current_user, "id", None))
        raise HTTPException(status_code=500, detail="Error interno obteniendo detalle de usuario") from e


# ---------------- Reemplazar sets vinculados (WRITE scoped) ----------------
@router.put(
    "/{user_id}/instituciones",
    response_model=List[int],
    summary="(ADMIN/GESTOR_SERVICIOS) Reemplaza instituciones vinculadas (scoped)",
)
def set_user_instituciones(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles(*USUARIOS_WRITE_ROLES))],
    payload: IdsPayload | None = Body(None),
):
    ids = payload.Ids if payload else []
    Log.info("PUT instituciones user_id=%s actor_id=%s roles=%s ids=%s", user_id, current_user.id, current_user.roles, ids)
    return svc.set_instituciones_scoped(db, user_id, ids, actor=current_user)


@router.put(
    "/{user_id}/servicios",
    response_model=List[int],
    summary="(ADMIN/GESTOR_SERVICIOS) Reemplaza servicios vinculados (scoped)",
)
def set_user_servicios(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles(*USUARIOS_WRITE_ROLES))],
    payload: IdsPayload | None = Body(None),
):
    ids = payload.Ids if payload else []
    Log.info("PUT servicios user_id=%s actor_id=%s roles=%s ids=%s", user_id, current_user.id, current_user.roles, ids)
    return svc.set_servicios_scoped(db, user_id, ids, actor=current_user)


@router.put(
    "/{user_id}/divisiones",
    response_model=List[int],
    summary="(ADMIN) Reemplaza divisiones vinculadas",
)
def set_user_divisiones(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles(*USUARIOS_ADMIN_ONLY))],
    payload: IdsPayload | None = Body(None),
):
    ids = payload.Ids if payload else []
    Log.info("PUT divisiones user_id=%s ids=%s", user_id, ids)
    return svc.set_divisiones(db, user_id, ids)


@router.put(
    "/{user_id}/unidades",
    response_model=List[int],
    summary="(ADMIN/GESTOR_SERVICIOS) Reemplaza unidades vinculadas (scoped)",
)
def set_user_unidades(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles(*USUARIOS_WRITE_ROLES))],
    payload: IdsPayload | None = Body(None),
):
    ids = payload.Ids if payload else []
    Log.info("PUT unidades user_id=%s actor_id=%s roles=%s ids=%s", user_id, current_user.id, current_user.roles, ids)
    return svc.set_unidades_scoped(db, user_id, ids, actor=current_user)


# ---------------- Activar / desactivar (ADMIN) ----------------
@router.put(
    "/{user_id}/activar",
    response_model=UserDetailFullDTO,
    summary="(ADMIN) Activar usuario (Active = true)",
)
def activar_usuario(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    request: Request,
    current_user: Annotated[UserPublic, Depends(require_roles(*USUARIOS_ADMIN_ONLY))],
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
    current_user: Annotated[UserPublic, Depends(require_roles(*USUARIOS_ADMIN_ONLY))],
):
    svc.set_active(db, user_id, False, actor_id=_actor_id(current_user, request))
    user, roles, inst_ids, srv_ids, div_ids, uni_ids = svc.get_detail(db, user_id)
    return _to_full_dto(user, roles, inst_ids, srv_ids, div_ids, uni_ids)


# ---------------- Roles (ADMIN) ----------------
@router.put(
    "/{user_id}/roles",
    response_model=list[str],
    summary="(ADMIN) Reemplaza roles del usuario",
)
def set_user_roles(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    payload: RolesPayload,
    _admin: Annotated[UserPublic, Depends(require_roles(*USUARIOS_ADMIN_ONLY))],
):
    Log.info("PUT roles user_id=%s roles=%s", user_id, getattr(payload, "roles", None))
    return svc.set_roles(db, user_id, payload.roles)


@router.get(
    "/{user_id}/vinculados-por-servicio",
    response_model=List[UserMiniDTO],
    summary="Usuarios vinculados por servicio (scoped) (ADMIN/GESTOR_SERVICIO/GESTOR DE CONSULTA)",
)
def get_usuarios_vinculados_por_servicio(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles(*USUARIOS_READ_ROLES))],
):
    try:
        items = svc.usuarios_vinculados_por_servicio_scoped(db, user_id, actor=current_user)

        out: list[UserMiniDTO] = []
        for it in (items or []):
            if isinstance(it, dict):
                u = it.get("user") or it.get("User") or it.get("usuario") or it
                dto = UserMiniDTO.model_validate(u)
                dto.ServicioIds = list(it.get("ServicioIds") or it.get("servicio_ids") or [])
                out.append(dto)
                continue

            if isinstance(it, (list, tuple)) and len(it) >= 2:
                u = it[0]
                svc_ids = it[1] or []
                dto = UserMiniDTO.model_validate(u)
                dto.ServicioIds = list(svc_ids)
                out.append(dto)
                continue

            dto = UserMiniDTO.model_validate(it)
            out.append(dto)

        return out

    except HTTPException:
        raise
    except Exception as e:
        Log.exception("Error vinculados-por-servicio target=%s actor=%s", user_id, getattr(current_user, "id", None))
        raise HTTPException(status_code=500, detail="Error interno obteniendo usuarios vinculados") from e


@router.get(
    "/{user_id}/unidades",
    response_model=List[UnidadSelectDTO],
    summary="Unidades vinculadas al usuario (scoped)",
)
def get_unidades_vinculadas_usuario(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles(*USUARIOS_READ_ROLES))],
):
    unidades = svc.unidades_vinculadas_scoped(db, user_id, actor=current_user)

    out: list[UnidadSelectDTO] = []
    for u in (unidades or []):
        if getattr(u, "Id", None) is None:
            continue
        dto = UnidadSelectDTO.model_validate(u)
        dto.Id = int(dto.Id)  # por si viene Decimal/int raro desde MSSQL
        out.append(dto)

    return out


@router.get(
    "/{user_id}/unidades/ids",
    response_model=List[int],
    summary="IDs de unidades vinculadas (scoped) (ADMIN/GESTOR_SERVICIO/GESTOR DE CONSULTA)",
)
def get_unidades_ids_vinculadas_usuario(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles(*USUARIOS_READ_ROLES))],
):
    try:
        unidades = svc.unidades_vinculadas_scoped(db, user_id, actor=current_user)
        return [int(u.Id) for u in (unidades or []) if getattr(u, "Id", None) is not None]
    except HTTPException:
        raise
    except Exception as e:
        Log.exception("Error get_unidades_ids_vinculadas_usuario target=%s actor=%s", user_id, getattr(current_user, "id", None))
        raise HTTPException(status_code=500, detail="Error interno obteniendo unidades vinculadas") from e
