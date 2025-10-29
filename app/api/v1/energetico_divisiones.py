from typing import Annotated, List, Optional, TypeAlias
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.energetico_division import (
    EnergeticoDivisionDTO,
    EnergeticoDivisionReplacePayload,
    EnergeticoDivisionCreateItem,
)
from app.services.energetico_division_service import EnergeticoDivisionService

router = APIRouter(prefix="/api/v1/energetico-divisiones", tags=["EnergeticoDivision"])
svc = EnergeticoDivisionService()

# Alias de tipo para evitar el warning de 
DbDep: TypeAlias = Annotated[Session, Depends(get_db)]

# =========================
# GET: listado por división
# =========================
@router.get(
    "/division/{division_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="Listado por división",
)
def list_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.list_by_division(db, division_id)


# ==========================================
# GET: divisiones que usan un energético X
# ==========================================
@router.get(
    "/energetico/{energetico_id}/divisiones",
    response_model=List[int],
    summary="Divisiones que usan un energético",
)
def divisiones_por_energetico(
    energetico_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.list_divisiones_by_energetico(db, energetico_id)


# ==============================================================
# PUT: reemplazar set completo de energéticos para una división
# ==============================================================
@router.put(
    "/division/{division_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="(ADMINISTRADOR) Reemplaza set para una división",
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def replace_set(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionReplacePayload,
    db: DbDep,
):
    items = [it.model_dump() for it in (payload.items or [])]
    return svc.replace_for_division(db, division_id, items)


# ==========================================
# POST: asignar energético a una división
# ==========================================
@router.post(
    "/division/{division_id}/assign",
    response_model=EnergeticoDivisionDTO,
    summary="(ADMINISTRADOR) Asignar un energético a la división",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def assign_energetico(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionCreateItem,  # EnergeticoId y NumeroClienteId
    db: DbDep,
):
    return svc.assign_to_division(
        db=db,
        division_id=division_id,
        energetico_id=payload.EnergeticoId,
        numero_cliente_id=payload.NumeroClienteId,
    )


# ===============================================
# DELETE: desasignar energético de una división
# ===============================================
@router.delete(
    "/division/{division_id}/energetico/{energetico_id}",
    summary="(ADMINISTRADOR) Desasignar un energético de la división",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def unassign_energetico(
    division_id: Annotated[int, Path(..., ge=1)],
    energetico_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,  # ← no-default antes del Query con default
    numero_cliente_id: Optional[int] = Query(
        None, ge=1, description="Opcional: si se usó un NumeroClienteId en la asignación"
    ),
):
    _ = svc.unassign_from_division(
        db=db,
        division_id=division_id,
        energetico_id=energetico_id,
        numero_cliente_id=numero_cliente_id,
    )
    # 204 No Content
    return None
