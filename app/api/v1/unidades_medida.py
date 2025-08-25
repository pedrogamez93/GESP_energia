# app/api/v1/unidades_medida.py
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.unidad_medida import (
    UnidadMedidaDTO, UnidadMedidaCreate, UnidadMedidaUpdate, UnidadMedidaSelectDTO
)
from app.services.unidad_medida_service import UnidadMedidaService

router = APIRouter(prefix="/api/v1/unidades-medida", tags=["Unidades de medida"])
svc = UnidadMedidaService()

DbDep = Annotated[Session, Depends(get_db)]

# ---- GET públicos ----
@router.get("", response_model=dict)
def list_unidades(
    db: DbDep,
    q: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    ...

@router.get("/select", response_model=list[UnidadMedidaSelectDTO])
def list_unidades_select(
    db: DbDep,
):
    rows = svc.list_select(db) or []   # <- si por alguna razón viniera None
    # rows de SQLAlchemy .all() ya es lista, pero protegemos por si el service cambia
    out = [UnidadMedidaSelectDTO(Id=int(r[0]), Nombre=r[1]) for r in rows]
    return out
    ...

@router.get("/{id}", response_model=UnidadMedidaDTO)
def get_unidad(
    db: DbDep,
    id: Annotated[int, Path(..., ge=1)],   # <-- db primero, y Path via Annotated
):
    ...

@router.post("", response_model=UnidadMedidaDTO, status_code=status.HTTP_201_CREATED)
def create_unidad(
    payload: UnidadMedidaCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    ...

@router.put("/{id}", response_model=UnidadMedidaDTO)
def update_unidad(
    id: int,
    payload: UnidadMedidaUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    ...

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unidad(
    id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    ...
