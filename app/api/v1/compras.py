from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.compra import (
    CompraDTO, CompraListDTO, CompraCreate, CompraUpdate,
    CompraMedidorItemDTO, CompraItemsPayload
)
from app.services.compra_service import CompraService

router = APIRouter(prefix="/api/v1/compras", tags=["Compras / Consumos"])
svc = CompraService()
DbDep = Annotated[Session, Depends(get_db)]


# ---- GET públicos ----
@router.get("", response_model=dict, summary="Listado paginado de compras/consumos")
def list_compras(
    db: DbDep,
    q: str | None = Query(default=None, description="Busca en Observacion"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    DivisionId: int | None = Query(default=None),
    EnergeticoId: int | None = Query(default=None),
    NumeroClienteId: int | None = Query(default=None),
    FechaDesde: str | None = Query(default=None),
    FechaHasta: str | None = Query(default=None),
):
    return svc.list(db, q, page, page_size, DivisionId, EnergeticoId, NumeroClienteId, FechaDesde, FechaHasta)


@router.get("/{compra_id}", response_model=CompraDTO, summary="Detalle (incluye items por medidor)")
def get_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    c = svc.get(db, compra_id)
    items = svc._items_by_compra(db, compra_id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


# ---- Escrituras (ADMINISTRADOR) ----
@router.post("", response_model=CompraDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear compra/consumo")
def create_compra(
    payload: CompraCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    c, items = svc.create(db, payload, created_by=current_user.id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.put("/{compra_id}", response_model=CompraDTO,
            summary="(ADMINISTRADOR) Actualizar compra/consumo")
def update_compra(
    compra_id: int,
    payload: CompraUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    c, items = svc.update(db, compra_id, payload, modified_by=current_user.id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.delete("/{compra_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar compra/consumo")
def delete_compra(
    compra_id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, compra_id)
    return None


# ---- Reemplazar items por medidor (ADMIN) ----
@router.put("/{compra_id}/medidores", response_model=List[CompraMedidorItemDTO],
            summary="(ADMINISTRADOR) Reemplaza los items de medidor para la compra")
def replace_items_compra(
    compra_id: int,
    payload: CompraItemsPayload,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    rows = svc.replace_items(db, compra_id, [x.model_dump() for x in (payload.Items or [])])
    return [CompraMedidorItemDTO.model_validate(x) for x in rows]


# ---- Resumen mensual simple ----
@router.get("/resumen/mensual", response_model=List[dict],
            summary="Resumen mensual por División/Energético (suma de Consumo y Costo)")
def resumen_mensual(
    db: DbDep,
    DivisionId: int = Query(..., ge=1),
    EnergeticoId: int = Query(..., ge=1),
    Desde: str = Query(..., description="YYYY-MM-01"),
    Hasta: str = Query(..., description="YYYY-MM-01 (exclusivo)"),
):
    return svc.resumen_mensual(db, DivisionId, EnergeticoId, Desde, Hasta)
