from __future__ import annotations
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.parametro_medicion import ParametroMedicionDTO
from app.services.parametro_medicion_service import ParametroMedicionService

router = APIRouter(prefix="/api/v1/parametros-medicion", tags=["Parámetros de medición"])
svc = ParametroMedicionService()
DbDep = Annotated[Session, Depends(get_db)]

@router.get("", response_model=List[ParametroMedicionDTO])
def list_parametros(db: DbDep, q: str | None = Query(default=None)):
    return [ParametroMedicionDTO.model_validate(x) for x in svc.list(db, q)]

@router.get("/{id}", response_model=ParametroMedicionDTO)
def get_parametro(db: DbDep, id: Annotated[int, Path(..., ge=1)]):
    return svc.get(db, id)
