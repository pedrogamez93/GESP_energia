from __future__ import annotations

import logging
from typing import Annotated, List, Optional, Tuple, TypeAlias

from fastapi import APIRouter, Depends, Path, Query, status, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.energetico_division import (
    EnergeticoDivisionDTO,
    EnergeticoDivisionReplacePayload,
    EnergeticoDivisionCreateItem,
)
from app.services.energetico_division_service import EnergeticoDivisionService
from app.services.unidad_scope import division_id_from_unidad

router = APIRouter(prefix="/api/v1/energetico-divisiones", tags=["EnergeticoDivision"])
svc = EnergeticoDivisionService()
DbDep: TypeAlias = Annotated[Session, Depends(get_db)]
Log = logging.getLogger(__name__)

# ==========================================================
# ✅ ROLES
#   - LECTURA: incluye GESTOR DE CONSULTA
#   - ESCRITURA: NO incluye GESTOR DE CONSULTA
# ==========================================================
ENERGETICO_DIVISION_READ_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_SERVICIO",
    "GESTOR_FLOTA",
    "GESTOR DE CONSULTA",
)

ENERGETICO_DIVISION_WRITE_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_SERVICIO",
    "GESTOR_FLOTA",
)

ReadUser = Annotated[UserPublic, Depends(require_roles(*ENERGETICO_DIVISION_READ_ROLES))]
WriteUser = Annotated[UserPublic, Depends(require_roles(*ENERGETICO_DIVISION_WRITE_ROLES))]

# ─────────────────────────────────────────────────────────────
# Scopes (si existen en tu proyecto)
# ─────────────────────────────────────────────────────────────
try:
    from app.db.models.usuarios_unidades import UsuarioUnidad  # type: ignore
except Exception:
    UsuarioUnidad = None  # type: ignore

try:
    from app.db.models.usuarios_divisiones import UsuarioDivision  # type: ignore
except Exception:
    UsuarioDivision = None  # type: ignore


def _is_admin(user: UserPublic) -> bool:
    return "ADMINISTRADOR" in (user.roles or [])


def _assert_user_can_access_unidad(db: Session, user: UserPublic, unidad_id: int) -> None:
    """
    ADMIN: ok.
    No-admin: debe tener la UnidadId en su alcance (UsuarioUnidad).

    Si no existe UsuarioUnidad, por seguridad NO abrimos.
    """
    if _is_admin(user):
        return

    if UsuarioUnidad is None:
        Log.warning(
            "forbidden_scope(no UsuarioUnidad) actor=%s roles=%s unidad_id=%s",
            getattr(user, "id", None),
            getattr(user, "roles", None),
            int(unidad_id),
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar alcance del usuario (UsuarioUnidad no disponible).",
                "unidad_id": int(unidad_id),
            },
        )

    ok = db.execute(
        select(UsuarioUnidad.UnidadId)
        .where(
            UsuarioUnidad.UsuarioId == user.id,
            UsuarioUnidad.UnidadId == int(unidad_id),
        )
        .limit(1)
    ).first()

    if not ok:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No tienes acceso a esta unidad (fuera de tu alcance).",
                "unidad_id": int(unidad_id),
            },
        )


def _assert_user_can_access_division(db: Session, user: UserPublic, division_id: int) -> None:
    """
    ADMIN: ok.
    No-admin: debe tener la DivisionId en su alcance (UsuarioDivision).

    Si no existe UsuarioDivision, por seguridad NO abrimos.
    """
    if _is_admin(user):
        return

    if UsuarioDivision is None:
        Log.warning(
            "forbidden_scope(no UsuarioDivision) actor=%s roles=%s division_id=%s",
            getattr(user, "id", None),
            getattr(user, "roles", None),
            int(division_id),
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar alcance del usuario (UsuarioDivision no disponible).",
                "division_id": int(division_id),
            },
        )

    ok = db.execute(
        select(UsuarioDivision.DivisionId)
        .where(
            UsuarioDivision.UsuarioId == user.id,
            UsuarioDivision.DivisionId == int(division_id),
        )
        .limit(1)
    ).first()

    if not ok:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No tienes acceso a esta división (fuera de tu alcance).",
                "division_id": int(division_id),
            },
        )


def _resolve_division_from_unidad_or_raise(db: Session, unidad_id: int) -> int:
    """
    UnidadId -> DivisionId (alias)
    """
    try:
        div = division_id_from_unidad(db, int(unidad_id))
        return int(div)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=404,
            detail={"code": "unidad_not_found", "msg": "UnidadId no encontrada"},
        )


def _require_role_for_write(user: UserPublic) -> None:
    """
    Guardia extra: aunque el dependency ya bloquea,
    dejamos un mensaje más claro si alguien intenta colarse.
    """
    if "GESTOR DE CONSULTA" in (user.roles or []) and not _is_admin(user):
        raise HTTPException(
            status_code=403,
            detail={"code": "forbidden_role", "msg": "GESTOR DE CONSULTA es solo lectura."},
        )


# =========================
# GET: listado por UNIDAD (lectura)
# =========================
@router.get(
    "/unidad/{unidad_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="Listado por unidad (alias: UnidadId -> DivisionId)",
)
def list_por_unidad(
    unidad_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    user: ReadUser,
):
    _assert_user_can_access_unidad(db, user, int(unidad_id))
    division_id = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    # (Opcional) si tu mapping real es solo por division:
    _assert_user_can_access_division(db, user, int(division_id))
    return svc.list_by_division(db, int(division_id))


# ==========================================
# PUT: reemplazar set por UNIDAD (write)
# ==========================================
@router.put(
    "/unidad/{unidad_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="(ADMIN/GESTOR_*) Reemplaza set para una unidad",
)
def replace_set_por_unidad(
    unidad_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionReplacePayload,
    db: DbDep,
    user: WriteUser,
):
    _require_role_for_write(user)
    _assert_user_can_access_unidad(db, user, int(unidad_id))
    division_id = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    _assert_user_can_access_division(db, user, int(division_id))

    items = [it.model_dump() for it in (payload.items or [])]
    return svc.replace_for_division(db, int(division_id), items)


# ==========================================
# POST: asignar energético a una UNIDAD (write)
# ==========================================
@router.post(
    "/unidad/{unidad_id}/assign",
    response_model=EnergeticoDivisionDTO,
    summary="(ADMIN/GESTOR_*) Asignar un energético a la unidad",
    status_code=status.HTTP_201_CREATED,
)
def assign_energetico_unidad(
    unidad_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionCreateItem,
    db: DbDep,
    user: WriteUser,
):
    _require_role_for_write(user)
    _assert_user_can_access_unidad(db, user, int(unidad_id))
    division_id = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    _assert_user_can_access_division(db, user, int(division_id))

    return svc.assign_to_division(
        db=db,
        division_id=int(division_id),
        energetico_id=payload.EnergeticoId,
        numero_cliente_id=payload.NumeroClienteId,
    )


# ==========================================
# DELETE: desasignar energético de una UNIDAD (write)
# ==========================================
@router.delete(
    "/unidad/{unidad_id}/energetico/{energetico_id}",
    summary="(ADMIN/GESTOR_*) Desasignar un energético de la unidad",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unassign_energetico_unidad(
    unidad_id: Annotated[int, Path(..., ge=1)],
    energetico_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    user: WriteUser,
    numero_cliente_id: Optional[int] = Query(None, ge=1),
):
    _require_role_for_write(user)
    _assert_user_can_access_unidad(db, user, int(unidad_id))
    division_id = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    _assert_user_can_access_division(db, user, int(division_id))

    svc.unassign_from_division(
        db=db,
        division_id=int(division_id),
        energetico_id=int(energetico_id),
        numero_cliente_id=numero_cliente_id,
    )
    return None


# =========================
# GET: listado por DIVISION (lectura)
# =========================
@router.get(
    "/division/{division_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="Listado por división (scoped para gestores)",
)
def list_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    user: ReadUser,
):
    _assert_user_can_access_division(db, user, int(division_id))
    return svc.list_by_division(db, int(division_id))


# ==========================================
# PUT: reemplazar set por DIVISION (write)
# ==========================================
@router.put(
    "/division/{division_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="(ADMIN/GESTOR_*) Reemplaza set para una división",
)
def replace_set_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionReplacePayload,
    db: DbDep,
    user: WriteUser,
):
    _require_role_for_write(user)
    _assert_user_can_access_division(db, user, int(division_id))

    items = [it.model_dump() for it in (payload.items or [])]
    return svc.replace_for_division(db, int(division_id), items)


@router.post(
    "/division/{division_id}/assign",
    response_model=EnergeticoDivisionDTO,
    summary="(ADMIN/GESTOR_*) Asignar un energético a la división",
    status_code=status.HTTP_201_CREATED,
)
def assign_energetico_division(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionCreateItem,
    db: DbDep,
    user: WriteUser,
):
    _require_role_for_write(user)
    _assert_user_can_access_division(db, user, int(division_id))

    return svc.assign_to_division(
        db=db,
        division_id=int(division_id),
        energetico_id=payload.EnergeticoId,
        numero_cliente_id=payload.NumeroClienteId,
    )


@router.delete(
    "/division/{division_id}/energetico/{energetico_id}",
    summary="(ADMIN/GESTOR_*) Desasignar un energético de la división",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unassign_energetico_division(
    division_id: Annotated[int, Path(..., ge=1)],
    energetico_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    user: WriteUser,
    numero_cliente_id: Optional[int] = Query(None, ge=1),
):
    _require_role_for_write(user)
    _assert_user_can_access_division(db, user, int(division_id))

    svc.unassign_from_division(
        db=db,
        division_id=int(division_id),
        energetico_id=int(energetico_id),
        numero_cliente_id=numero_cliente_id,
    )
    return None
