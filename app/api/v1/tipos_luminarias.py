# app/api/v1/tipos_luminarias.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.tipo_luminaria import (
    TipoLuminariaDTO, TipoLuminariaSelectDTO, TipoLuminariaCreate, TipoLuminariaUpdate
)
from app.services.tipo_luminaria_service import TipoLuminariaService

router = APIRouter(prefix="/api/v1/tipos-luminarias", tags=["Tipos de luminarias"])
svc = TipoLuminariaService()
DbDep = Annotated[Session, Depends(get_db)]

@router.get("", response_model=dict)
def list_tipos_luminarias(
    db: DbDep,
    q: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return svc.list(db, q, page, page_size)

@router.get("/select", response_model=List[TipoLuminariaSelectDTO])
def select_tipos_luminarias(
    db: DbDep,
    q: str | None = Query(default=None),
):
    rows = svc.list_select(db, q)
    return [TipoLuminariaSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]

@router.get("/{id}", response_model=TipoLuminariaDTO)
def get_tipo_luminaria(
    db: DbDep,
    id: Annotated[int, Path(..., ge=1)],
):
    return svc.get(db, id)

@router.post("", response_model=TipoLuminariaDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear tipo de luminaria")
def create_tipo_luminaria(
    payload: TipoLuminariaCreate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.create(db, payload)

@router.put("/{id}", response_model=TipoLuminariaDTO,
            summary="(ADMINISTRADOR) Actualizar tipo de luminaria")
def update_tipo_luminaria(
    id: int,
    payload: TipoLuminariaUpdate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.update(db, id, payload)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar tipo de luminaria")
def delete_tipo_luminaria(
    id: int,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, id)
    return None
