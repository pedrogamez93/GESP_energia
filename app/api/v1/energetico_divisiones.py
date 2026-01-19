from __future__ import annotations

import logging
from typing import Annotated, List, Optional, TypeAlias

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

# ✅ Mismos roles que en Compras/Sistemas
ENERGETICO_DIVISION_WRITE_ROLES = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_SERVICIO",
    "GESTOR_FLOTA",
)

CurrentUser = Annotated[UserPublic, Depends(require_roles(*ENERGETICO_DIVISION_WRITE_ROLES))]

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


def _assert_user_can_manage_unidad(db: Session, user: UserPublic, unidad_id: int) -> None:
    """
    ADMIN: ok.
    Gestores: deben tener la UnidadId en su alcance (UsuarioUnidad).

    Si no existe UsuarioUnidad, por seguridad no abrimos.
    """
    if _is_admin(user):
        return

    if UsuarioUnidad is None:
        Log.warning(
            "forbidden_scope (no UsuarioUnidad) actor=%s roles=%s unidad_id=%s",
            getattr(user, "id", None),
            user.roles,
            unidad_id,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar alcance del gestor (UsuarioUnidad no disponible).",
                "unidad_id": unidad_id,
            },
        )

    ok = db.execute(
        select(UsuarioUnidad.UnidadId).where(
            UsuarioUnidad.UsuarioId == user.id,
            UsuarioUnidad.UnidadId == int(unidad_id),
        )
    ).first()

    if not ok:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No puedes gestionar esta unidad (fuera de tu alcance).",
                "unidad_id": int(unidad_id),
            },
        )


def _assert_user_can_manage_division(db: Session, user: UserPublic, division_id: int) -> None:
    """
    ADMIN: ok.
    Gestores: deben tener la DivisionId en su alcance (UsuarioDivision).

    Si no existe UsuarioDivision, por seguridad no abrimos.
    """
    if _is_admin(user):
        return

    if UsuarioDivision is None:
        Log.warning(
            "forbidden_scope (no UsuarioDivision) actor=%s roles=%s division_id=%s",
            getattr(user, "id", None),
            user.roles,
            division_id,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar alcance del gestor (UsuarioDivision no disponible).",
                "division_id": division_id,
            },
        )

    ok = db.execute(
        select(UsuarioDivision.DivisionId).where(
            UsuarioDivision.UsuarioId == user.id,
            UsuarioDivision.DivisionId == int(division_id),
        )
    ).first()

    if not ok:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No puedes gestionar esta división (fuera de tu alcance).",
                "division_id": int(division_id),
            },
        )


def _resolve_division_from_unidad_or_raise(db: Session, unidad_id: int) -> int:
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


# =========================
# GET: listado por UNIDAD
# =========================
@router.get(
    "/unidad/{unidad_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="Listado por unidad (alias: UnidadId -> DivisionId)",
)
def list_por_unidad(
    unidad_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    user: CurrentUser,
):
    _assert_user_can_manage_unidad(db, user, int(unidad_id))
    division_id = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    # (opcional) también valida división si tienes UsuarioDivision consistente
    # _assert_user_can_manage_division(db, user, int(division_id))
    return svc.list_by_division(db, division_id)


# ==========================================
# PUT: reemplazar set por UNIDAD
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
    user: CurrentUser,
):
    _assert_user_can_manage_unidad(db, user, int(unidad_id))
    division_id = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    items = [it.model_dump() for it in (payload.items or [])]
    return svc.replace_for_division(db, division_id, items)


# ==========================================
# POST: asignar energético a una UNIDAD
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
    user: CurrentUser,
):
    _assert_user_can_manage_unidad(db, user, int(unidad_id))
    division_id = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    return svc.assign_to_division(
        db=db,
        division_id=division_id,
        energetico_id=payload.EnergeticoId,
        numero_cliente_id=payload.NumeroClienteId,
    )


# ==========================================
# DELETE: desasignar energético de una UNIDAD
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
    user: CurrentUser,
    numero_cliente_id: Optional[int] = Query(None, ge=1),
):
    _assert_user_can_manage_unidad(db, user, int(unidad_id))
    division_id = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    svc.unassign_from_division(
        db=db,
        division_id=division_id,
        energetico_id=int(energetico_id),
        numero_cliente_id=numero_cliente_id,
    )
    return None


# =========================
# GET: listado por DIVISION
# =========================
@router.get(
    "/division/{division_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="Listado por división (scoped para gestores)",
)
def list_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    user: CurrentUser,
):
    _assert_user_can_manage_division(db, user, int(division_id))
    return svc.list_by_division(db, int(division_id))


@router.put(
    "/division/{division_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="(ADMIN/GESTOR_*) Reemplaza set para una división",
)
def replace_set_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionReplacePayload,
    db: DbDep,
    user: CurrentUser,
):
    _assert_user_can_manage_division(db, user, int(division_id))
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
    user: CurrentUser,
):
    _assert_user_can_manage_division(db, user, int(division_id))
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
    user: CurrentUser,
    numero_cliente_id: Optional[int] = Query(None, ge=1),
):
    _assert_user_can_manage_division(db, user, int(division_id))
    svc.unassign_from_division(
        db=db,
        division_id=int(division_id),
        energetico_id=int(energetico_id),
        numero_cliente_id=numero_cliente_id,
    )
    return None
