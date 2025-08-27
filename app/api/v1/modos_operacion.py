# app/api/v1/modos_operacion.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.modo_operacion import (
    ModoOperacionDTO, ModoOperacionSelectDTO, ModoOperacionCreate, ModoOperacionUpdate
)
from app.services.modo_operacion_service import ModoOperacionService

router = APIRouter(prefix="/api/v1/modos-operacion", tags=["Modos de operación"])
svc = ModoOperacionService()
DbDep = Annotated[Session, Depends(get_db)]

@router.get("", response_model=dict)
def list_modos(
    db: DbDep,
    q: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return svc.list(db, q, page, page_size)

@router.get("/select", response_model=List[ModoOperacionSelectDTO])
def select_modos(
    db: DbDep,
    q: str | None = Query(default=None),
):
    rows = svc.list_select(db, q)
    return [ModoOperacionSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]

@router.get("/{id}", response_model=ModoOperacionDTO)
def get_modo(
    db: DbDep,
    id: Annotated[int, Path(..., ge=1)],
):
    return svc.get(db, id)

@router.post("", response_model=ModoOperacionDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear modo de operación")
def create_modo(
    payload: ModoOperacionCreate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.create(db, payload)

@router.put("/{id}", response_model=ModoOperacionDTO,
            summary="(ADMINISTRADOR) Actualizar modo de operación")
def update_modo(
    id: int,
    payload: ModoOperacionUpdate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.update(db, id, payload)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar modo de operación")
def delete_modo(
    id: int,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, id)
    return None
