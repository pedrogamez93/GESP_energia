from __future__ import annotations

from typing import Annotated, List, Optional
import logging

from fastapi import APIRouter, Body, Depends, Path, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.unidad import UnidadSelectDTO
from app.schemas.usuario_vinculo import (
    IdsPayload,
    UserDetailFullDTO,
    UnidadMiniDTO,
    UserMiniDTO,  # 👈 necesario para response_model=List[UserMiniDTO]
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

# ✅ Lecturas: Admin + Gestor Servicios + Gestor Consulta (scoped en service)
USUARIOS_READ_ROLES = (ROLE_ADMIN, ROLE_GESTOR_SERVICIO, ROLE_GESTOR_CONSULTA)

# ✅ Escrituras: Admin + Gestor Servicios (NO consulta)
USUARIOS_WRITE_ROLES = (ROLE_ADMIN, ROLE_GESTOR_SERVICIO)

# ✅ Debug/roles/activar/desactivar: solo Admin
USUARIOS_ADMIN_ONLY = (ROLE_ADMIN,)


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
    e inyecta roles y sets vinculados.
    """
    base = UserDetailFullDTO.model_validate(user)  # toma todos los campos del modelo
    base.Roles = roles or []
    base.InstitucionIds = inst_ids or []
    base.ServicioIds = srv_ids or []
    base.DivisionIds = div_ids or []
    base.UnidadIds = uni_ids or []
    return base


def _assert_can_read_user_detail(actor: UserPublic, target_user_id: str) -> None:
    """
    Seguridad mínima aquí:
    - ADMIN: ok
    - Otros (incluye GESTOR_SERVICIOS y GESTOR DE CONSULTA): permitido, PERO el service debe aplicar scope.
      Si tu service hoy NO aplica scope al leer detalle, esto hay que reforzarlo ahí.
    """
    if ROLE_ADMIN in (actor.roles or []):
        return
    # No bloqueamos aquí, porque el alcance real lo impone el service con joins scoped.
    return


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
            "unidades": "/api/v1/usuarios/{user_id}/unidades (WRITE: ADMIN/GESTOR_SERVICIOS, SCOPED)",
            "roles": "/api/v1/usuarios/{user_id}/roles (ADMIN)",
            "activar": "/api/v1/usuarios/{user_id}/activar (ADMIN)",
            "desactivar": "/api/v1/usuarios/{user_id}/desactivar (ADMIN)",
        },
    }


# ---------------- DEBUG: ver lo que el backend ve en UsuariosUnidades -----------
@router.get(
    "/{user_id}/debug-unidades",
    summary="DEBUG: Unidades vinculadas según la BD que ve el backend",
)
def debug_unidades_usuario(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles(*USUARIOS_ADMIN_ONLY))],
):
    rows = db.execute(
        select(UsuarioUnidad.UsuarioId, UsuarioUnidad.UnidadId)
        .where(UsuarioUnidad.UsuarioId == user_id)
    ).all()
    Log.info("DEBUG-unidades user_id=%s rows=%s", user_id, rows)
    return [{"UsuarioId": r[0], "UnidadId": r[1]} for r in rows]


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
    # ✅ Para GESTOR_SERVICIOS y GESTOR DE CONSULTA esto debe ser SCOPED.
    #    Si el service aún no filtra por actor, hay que reforzarlo allá.
    _assert_can_read_user_detail(current_user, user_id)

    try:
        # Preferimos método scoped si existe
        if hasattr(svc, "get_detail_scoped"):
            user, roles, inst_ids, srv_ids, div_ids, uni_ids = svc.get_detail_scoped(db, user_id, actor=current_user)
        else:
            # Fallback al método actual (OJO: si no filtra, hay riesgo de fuga).
            user, roles, inst_ids, srv_ids, div_ids, uni_ids = svc.get_detail(db, user_id)

            # Medida defensiva: si no es admin y el service no es scoped, bloqueamos para no filtrar usuarios globales
            if ROLE_ADMIN not in (current_user.roles or []):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "forbidden_scope",
                        "msg": "Este endpoint requiere lectura scoped. Implementa get_detail_scoped en UsuarioVinculoService.",
                    },
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
    Log.info(
        "PUT instituciones user_id=%s actor_id=%s actor_roles=%s requested_ids=%s",
        user_id, current_user.id, current_user.roles, ids,
    )
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
    Log.info(
        "PUT servicios user_id=%s actor_id=%s actor_roles=%s requested_ids=%s",
        user_id, current_user.id, current_user.roles, ids,
    )
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
    Log.info("PUT divisiones user_id=%s normalized_ids=%s", user_id, ids)
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
    Log.info(
        "PUT unidades user_id=%s actor_id=%s actor_roles=%s requested_ids=%s",
        user_id, current_user.id, current_user.roles, ids,
    )
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
    Log.info("PUT activar usuario %s", user_id)
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
    Log.info("PUT desactivar usuario %s", user_id)
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
    """
    Retorna usuarios que comparten al menos un servicio con `user_id`.
    Además, incluye `ServicioIds` = lista de servicios en común con el usuario base.

    El scoping (qué puede ver un GESTOR) lo impone el service:
      - ADMIN: sin restricción
      - GESTOR_SERVICIO / GESTOR DE CONSULTA: limitado a su alcance
    """
    try:
        items = svc.usuarios_vinculados_por_servicio_scoped(db, user_id, actor=current_user)

        # Soporta 2 formatos de retorno desde el service:
        #  1) [{'user': <AspNetUser o dict>, 'ServicioIds': [..]}, ...]
        #  2) [<AspNetUser>, ...]  (en ese caso el DTO saldrá sin ServicioIds)
        out: list[UserMiniDTO] = []
        for it in (items or []):
            # Caso A: viene como dict con user + ServicioIds
            if isinstance(it, dict):
                u = it.get("user") or it.get("User") or it.get("usuario") or it
                dto = UserMiniDTO.model_validate(u)
                dto.ServicioIds = list(it.get("ServicioIds") or it.get("servicio_ids") or [])
                out.append(dto)
                continue

            # Caso B: viene como tupla (user, ServicioIds)
            if isinstance(it, (list, tuple)) and len(it) >= 2:
                u = it[0]
                svc_ids = it[1] or []
                dto = UserMiniDTO.model_validate(u)
                dto.ServicioIds = list(svc_ids)
                out.append(dto)
                continue

            # Caso C: viene el modelo directo (AspNetUser)
            dto = UserMiniDTO.model_validate(it)
            out.append(dto)

        return out

    except HTTPException:
        raise
    except Exception as e:
        Log.exception(
            "Error vinculados-por-servicio target=%s actor=%s roles=%s",
            user_id,
            getattr(current_user, "id", None),
            getattr(current_user, "roles", None),
        )
        raise HTTPException(status_code=500, detail="Error interno obteniendo usuarios vinculados") from e

@router.get(
    "/{user_id}/unidades",
    response_model=list[UnidadSelectDTO],
    summary="Unidades vinculadas al usuario (scoped)",
)
def get_unidades_vinculadas_usuario(
    user_id: Annotated[str, Path(...)],
    db: DbDep,
    current_user: CurrentUser,
):
    return svc.unidades_vinculadas_scoped(db, user_id, actor=current_user)
    
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
        Log.exception(
            "Error get_unidades_ids_vinculadas_usuario target=%s actor=%s roles=%s",
            user_id, getattr(current_user, "id", None), getattr(current_user, "roles", None),
        )
        raise HTTPException(status_code=500, detail="Error interno obteniendo unidades vinculadas") from e