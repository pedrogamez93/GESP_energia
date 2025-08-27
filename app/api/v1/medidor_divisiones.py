from typing import Annotated, List
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.medidor_division import MedidorDivisionDTO, IdsPayload
from app.services.medidor_division_service import MedidorDivisionService

router = APIRouter(prefix="/api/v1/medidor-divisiones", tags=["MedidorDivision"])
svc = MedidorDivisionService()
DbDep = Annotated[Session, Depends(get_db)]

@router.get("/division/{division_id}", response_model=List[MedidorDivisionDTO],
            summary="Medidores asociados a una división")
def list_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.list_by_division(db, division_id)

@router.get("/medidor/{medidor_id}/divisiones", response_model=List[int],
            summary="Divisiones asociadas a un medidor")
def list_divisiones_por_medidor(
    medidor_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.list_divisiones_by_medidor(db, medidor_id)

@router.put("/division/{division_id}", response_model=List[MedidorDivisionDTO],
            summary="(ADMINISTRADOR) Reemplaza set de medidores para una división")
def replace_set(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: IdsPayload,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.replace_for_division(db, division_id, payload.Ids or [])
