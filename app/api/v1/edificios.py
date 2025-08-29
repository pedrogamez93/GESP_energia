# app/api/v1/edificios.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.edificio import (
    EdificioDTO, EdificioListDTO, EdificioSelectDTO,
    EdificioCreate, EdificioUpdate
)
from app.services.edificio_service import EdificioService

router = APIRouter(prefix="/api/v1/edificios", tags=["Edificios"])
svc = EdificioService()
DbDep = Annotated[Session, Depends(get_db)]

# --- GET públicos ---
@router.get("", response_model=dict, summary="Listado paginado de edificios")
def list_edificios(
    db: DbDep,
    q: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    ComunaId: int | None = Query(default=None),
    active: bool | None = Query(default=True),  # <- NUEVO
):
    return svc.list(db, q, page, page_size, ComunaId, active)

@router.get("/select", response_model=List[EdificioSelectDTO], summary="Select (Id, Nombre)")
def select_edificios(
    db: DbDep,
    q: str | None = Query(default=None),
    ComunaId: int | None = Query(default=None),
):
    rows = svc.list_select(db, q, ComunaId)
    return [EdificioSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]

@router.get("/{id}", response_model=EdificioDTO, summary="Detalle de edificio")
def get_edificio(
    id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.get(db, id)

# --- ADMIN ---
@router.post("", response_model=EdificioDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear edificio")
def create_edificio(
    payload: EdificioCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.create(db, payload.model_dump(exclude_unset=True), created_by=current_user.id)
    return obj

@router.put("/{id}", response_model=EdificioDTO,
            summary="(ADMINISTRADOR) Actualizar edificio")
def update_edificio(
    id: int,
    payload: EdificioUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.update(db, id, payload.model_dump(exclude_unset=True), modified_by=current_user.id)
    return obj

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar edificio (soft-delete)")
def delete_edificio(
    id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.soft_delete(db, id, modified_by=current_user.id)
    return None

@router.patch("/{id}/reactivar", response_model=EdificioDTO,
              summary="(ADMINISTRADOR) Reactivar edificio")
def reactivate_edificio(
    id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.reactivate(db, id, modified_by=current_user.id)
    return obj
