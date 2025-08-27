from typing import Annotated, List
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.medidor_vinculo import IdsPayload, MedidorMiniDTO
from app.services.medidor_vinculo_service import MedidorVinculoService

router = APIRouter(prefix="/api/v1/medidores", tags=["Medidores"])
svc = MedidorVinculoService()
DbDep = Annotated[Session, Depends(get_db)]

# --- consultas ---
@router.get("/por-division/{division_id}", response_model=List[MedidorMiniDTO],
            summary="Lista medidores asociados a una división (vía tabla N-N)")
def medidores_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    items = svc.medidores_por_division(db, division_id)
    return [MedidorMiniDTO.model_validate(x) for x in items]

@router.get("/por-numero-cliente/{num_cliente_id}", response_model=List[MedidorMiniDTO],
            summary="Lista medidores por NumeroClienteId")
def medidores_por_numero_cliente(
    num_cliente_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    items = svc.medidores_por_numero_cliente(db, num_cliente_id)
    return [MedidorMiniDTO.model_validate(x) for x in items]

# --- escrituras (ADMINISTRADOR) ---
@router.put("/{medidor_id}/divisiones", response_model=List[int],
            summary="(ADMINISTRADOR) Reemplaza divisiones asociadas al medidor (tabla N-N)")
def set_divisiones_para_medidor(
    medidor_id: Annotated[int, Path(..., ge=1)],
    payload: IdsPayload | None,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    ids = payload.Ids if payload else []
    return svc.set_divisiones_para_medidor(db, medidor_id, ids)
