from __future__ import annotations
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.unidad_medida import (
    UnidadMedidaDTO,
    UnidadMedidaCreate,
    UnidadMedidaUpdate,
    UnidadMedidaPage,
)
from app.services.unidad_medida_service import UnidadMedidaService

router = APIRouter(prefix="/api/v1/unidades-medida", tags=["Unidades de medida"])
svc = UnidadMedidaService()
DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=UnidadMedidaPage)
def list_unidades(
    db: DbDep,
    q: str | None = Query(
        default=None,
        description="Texto de búsqueda para filtrar por nombre (ej: 'kilowatt', 'litro')",
    ),
    page: int = Query(1, ge=1, description="Número de página (mínimo 1)"),
    page_size: int = Query(50, ge=1, le=200, description="Registros por página (1–200)"),
):
    res = svc.list(db, q, page, page_size)
    items = [UnidadMedidaDTO.model_validate(it) for it in (res.get("data") or [])]
    return UnidadMedidaPage(total=int(res.get("total") or 0), data=items)


@router.get("/{id}", response_model=UnidadMedidaDTO)
def get_unidad(
    db: DbDep,
    id: Annotated[int, Path(..., ge=1, description="ID de la unidad de medida")],
):
    return svc.get(db, id)


@router.post(
    "",
    response_model=UnidadMedidaDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMINISTRADOR) Crear unidad de medida",
)
def create_unidad(
    payload: UnidadMedidaCreate,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.create(db, payload)


@router.put(
    "/{id}",
    response_model=UnidadMedidaDTO,
    summary="(ADMINISTRADOR) Actualizar unidad de medida",
)
def update_unidad(
    id: int,
    payload: UnidadMedidaUpdate,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.update(db, id, payload)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMINISTRADOR) Eliminar unidad de medida",
)
def delete_unidad(
    id: int,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, id)
    return None
