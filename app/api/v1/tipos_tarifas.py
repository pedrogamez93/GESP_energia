from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.tipo_tarifa import TipoTarifaDTO, TipoTarifaCreate, TipoTarifaUpdate
from app.services.tipo_tarifa_service import TipoTarifaService

router = APIRouter(prefix="/api/v1/tipo-tarifas", tags=["TipoTarifas"])
svc = TipoTarifaService()
DbDep = Annotated[Session, Depends(get_db)]

@router.get("", response_model=List[TipoTarifaDTO], summary="Listado simple")
def list_tipo_tarifas(
    db: DbDep,
    q: str | None = Query(default=None),
):
    return [TipoTarifaDTO.model_validate(x) for x in svc.list(db, q)]

@router.get("/{tipo_tarifa_id}", response_model=TipoTarifaDTO, summary="Detalle")
def get_tipo_tarifa(
    tipo_tarifa_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.get(db, tipo_tarifa_id)

@router.post("", response_model=TipoTarifaDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear tipo de tarifa")
def create_tipo_tarifa(
    payload: TipoTarifaCreate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.create(db, payload.Nombre)

@router.put("/{tipo_tarifa_id}", response_model=TipoTarifaDTO,
            summary="(ADMINISTRADOR) Renombrar tipo de tarifa")
def update_tipo_tarifa(
    tipo_tarifa_id: int,
    payload: TipoTarifaUpdate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.update(db, tipo_tarifa_id, payload.Nombre)

@router.delete("/{tipo_tarifa_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar tipo de tarifa")
def delete_tipo_tarifa(
    tipo_tarifa_id: int,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, tipo_tarifa_id)
    return None
