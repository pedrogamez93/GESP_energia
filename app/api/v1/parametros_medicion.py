from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.parametro_medicion import ParametroMedicionDTO, ParametroMedicionCreate, ParametroMedicionUpdate
from app.services.parametro_medicion_service import ParametroMedicionService

router = APIRouter(prefix="/api/v1/parametros-medicion", tags=["Parámetros de medición"])
svc = ParametroMedicionService()
DbDep = Annotated[Session, Depends(get_db)]

@router.get("", response_model=List[ParametroMedicionDTO], summary="Listado simple")
def list_parametros_medicion(db: DbDep, q: str | None = Query(default=None)):
    return [ParametroMedicionDTO.model_validate(x) for x in svc.list(db, q)]

@router.get("/{pm_id}", response_model=ParametroMedicionDTO, summary="Detalle")
def get_parametro_medicion(pm_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    return svc.get(db, pm_id)

@router.post("", response_model=ParametroMedicionDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear parámetro de medición")
def create_parametro_medicion(payload: ParametroMedicionCreate, db: DbDep,
                              _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    return svc.create(db, payload.Nombre)

@router.put("/{pm_id}", response_model=ParametroMedicionDTO,
            summary="(ADMINISTRADOR) Renombrar parámetro de medición")
def update_parametro_medicion(pm_id: int, payload: ParametroMedicionUpdate, db: DbDep,
                              _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    return svc.update(db, pm_id, payload.Nombre)

@router.delete("/{pm_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar parámetro de medición")
def delete_parametro_medicion(pm_id: int, db: DbDep,
                              _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    svc.delete(db, pm_id); return None
