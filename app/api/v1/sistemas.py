# app/api/v1/sistemas.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.sistema import (
    SistemaDTO, SistemaSelectDTO, SistemaCreate, SistemaUpdate
)
from app.services.sistema_service import SistemaService

router = APIRouter(prefix="/api/v1/sistemas", tags=["Sistemas"])
svc = SistemaService()
DbDep = Annotated[Session, Depends(get_db)]

@router.get("", response_model=dict)
def list_sistemas(
    db: DbDep,
    q: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return svc.list(db, q, page, page_size)

@router.get("/select", response_model=List[SistemaSelectDTO])
def select_sistemas(
    db: DbDep,
    q: str | None = Query(default=None),
):
    rows = svc.list_select(db, q)
    return [SistemaSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]

@router.get("/{id}", response_model=SistemaDTO)
def get_sistema(
    db: DbDep,
    id: Annotated[int, Path(..., ge=1)],
):
    return svc.get(db, id)

@router.post("", response_model=SistemaDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear sistema")
def create_sistema(
    payload: SistemaCreate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.create(db, payload)

@router.put("/{id}", response_model=SistemaDTO,
            summary="(ADMINISTRADOR) Actualizar sistema")
def update_sistema(
    id: int,
    payload: SistemaUpdate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.update(db, id, payload)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar sistema")
def delete_sistema(
    id: int,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, id)
    return None
