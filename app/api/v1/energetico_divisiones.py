from typing import Annotated, List, Optional, TypeAlias
from fastapi import APIRouter, Depends, Path, Query, status, HTTPException
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

# ✅ inyecta usuario (sirve para validar permisos por unidad)
CurrentUser = Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR", "GESTOR_UNIDAD"))]


# ─────────────────────────────────────────────────────────────
# TODO: Implementa esto con tu lógica real de permisos
# ─────────────────────────────────────────────────────────────
def _assert_user_can_manage_unidad(db: Session, user: UserPublic, unidad_id: int) -> None:
    # ADMIN pasa siempre
    if "ADMINISTRADOR" in (user.roles or []):
        return

    # ✅ Aquí va TU validación real:
    # - ejemplo: usuario_unidad / usuario_division / usuario_servicio, etc.
    # - si NO tiene acceso -> 403
    #
    # if not db.execute(...).scalar():
    #     raise HTTPException(403, detail={"code":"forbidden","msg":"No tienes acceso a esta unidad"})

    return  # ← quita esto cuando metas la validación real


def _resolve_division_from_unidad_or_raise(db: Session, unidad_id: int) -> int:
    try:
        div = division_id_from_unidad(db, int(unidad_id))
        return int(div)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail={"code": "unidad_not_found", "msg": "UnidadId no encontrada"})


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
    return svc.list_by_division(db, division_id)


# ==========================================
# PUT: reemplazar set por UNIDAD
# ==========================================
@router.put(
    "/unidad/{unidad_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="(ADMIN/GESTOR_UNIDAD) Reemplaza set para una unidad",
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
    summary="(ADMIN/GESTOR_UNIDAD) Asignar un energético a la unidad",
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
    summary="(ADMIN/GESTOR_UNIDAD) Desasignar un energético de la unidad",
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
        energetico_id=energetico_id,
        numero_cliente_id=numero_cliente_id,
    )
    return None

# =========================
# GET: listado por DIVISION
# =========================
@router.get(
    "/division/{division_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="Listado por división",
)
def list_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    user: CurrentUser,
):
    # si quieres, aquí también podrías validar acceso (si tienes mapping user->division)
    return svc.list_by_division(db, int(division_id))


@router.post(
    "/division/{division_id}/assign",
    response_model=EnergeticoDivisionDTO,
    summary="(ADMIN/GESTOR_UNIDAD) Asignar un energético a la división",
    status_code=status.HTTP_201_CREATED,
)
def assign_energetico_division(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionCreateItem,
    db: DbDep,
    user: CurrentUser,
):
    return svc.assign_to_division(
        db=db,
        division_id=int(division_id),
        energetico_id=payload.EnergeticoId,
        numero_cliente_id=payload.NumeroClienteId,
    )