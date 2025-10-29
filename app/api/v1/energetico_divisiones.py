from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.energetico_division import (
    EnergeticoDivisionDTO,
    EnergeticoDivisionReplacePayload,
    EnergeticoDivisionCreateItem,   # ← usamos tu esquema
)
from app.services.energetico_division_service import EnergeticoDivisionService

router = APIRouter(prefix="/api/v1/energetico-divisiones", tags=["EnergeticoDivision"])
svc = EnergeticoDivisionService()
DbDep = Annotated[Session, Depends(get_db)]

# ... (deja tus endpoints GET/PUT existentes)

@router.post(
    "/division/{division_id}/assign",
    response_model=EnergeticoDivisionDTO,
    summary="(ADMINISTRADOR) Asignar un energético a la división",
    status_code=status.HTTP_201_CREATED,
)
def assign_energetico(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionCreateItem,   # ← EnergeticoId y NumeroClienteId
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.assign_to_division(
        db=db,
        division_id=division_id,
        energetico_id=payload.EnergeticoId,
        numero_cliente_id=payload.NumeroClienteId,
    )

@router.delete(
    "/division/{division_id}/energetico/{energetico_id}",
    summary="(ADMINISTRADOR) Desasignar un energético de la división",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unassign_energetico(
    division_id: Annotated[int, Path(..., ge=1)],
    energetico_id: Annotated[int, Path(..., ge=1)],
    numero_cliente_id: Optional[int] = Query(
        None, ge=1, description="Opcional: si se usó un NumeroClienteId en la asignación"
    ),
    db: DbDep = Depends(get_db),
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))] = None,
):
    _ = svc.unassign_from_division(
        db=db,
        division_id=division_id,
        energetico_id=energetico_id,
        numero_cliente_id=numero_cliente_id,
    )
    return None  # 204 sin cuerpo
