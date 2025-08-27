from typing import Annotated, List
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.energetico_division import (
    EnergeticoDivisionDTO, EnergeticoDivisionReplacePayload
)
from app.services.energetico_division_service import EnergeticoDivisionService

router = APIRouter(prefix="/api/v1/energetico-divisiones", tags=["EnergeticoDivision"])
svc = EnergeticoDivisionService()
DbDep = Annotated[Session, Depends(get_db)]

@router.get("/division/{division_id}", response_model=List[EnergeticoDivisionDTO],
            summary="Listado por división")
def list_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.list_by_division(db, division_id)

@router.get("/energetico/{energetico_id}/divisiones", response_model=List[int],
            summary="Divisiones que usan un energético")
def divisiones_por_energetico(
    energetico_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.list_divisiones_by_energetico(db, energetico_id)

@router.put("/division/{division_id}", response_model=List[EnergeticoDivisionDTO],
            summary="(ADMINISTRADOR) Reemplaza set para una división")
def replace_set(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionReplacePayload,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    items = [it.model_dump() for it in (payload.items or [])]
    return svc.replace_for_division(db, division_id, items)
