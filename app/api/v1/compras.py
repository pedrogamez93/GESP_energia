# app/api/routes/compras.py
from __future__ import annotations
from typing import Annotated, List, Union

from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.compra import (
    CompraDTO, CompraListDTO, CompraCreate, CompraUpdate,
    CompraMedidorItemDTO, CompraItemsPayload, CompraPage,
    CompraFullPage, CompraListFullDTO, CompraFullDetalleDTO
)
from app.services.compra_service import CompraService

router = APIRouter(prefix="/api/v1/compras", tags=["Compras / Consumos"])
DbDep = Annotated[Session, Depends(get_db)]
svc = CompraService()


@router.get(
    "",
    summary="Listado paginado de compras/consumos (básico o enriquecido)",
    response_model=CompraFullPage  # <- usa el modelo completo
)
def list_compras(
    db: DbDep,
    q: str | None = Query(default=None, description="Busca en Observacion"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    DivisionId: int | None = Query(default=None),
    ServicioId: int | None = Query(default=None),
    EnergeticoId: int | None = Query(default=None),
    NumeroClienteId: int | None = Query(default=None),
    FechaDesde: str | None = Query(default=None),
    FechaHasta: str | None = Query(default=None),
    active: bool | None = Query(default=True),
    MedidorId: int | None = Query(default=None),
    EstadoValidacionId: str | None = Query(default=None),
    RegionId: int | None = Query(default=None),
    EdificioId: int | None = Query(default=None),
    NombreOpcional: str | None = Query(default=None),
    full: bool = Query(default=True)  # por defecto enriquecido
):
    if full:
        total, items = svc.list_full(
            db, q, page, page_size,
            DivisionId, ServicioId, EnergeticoId, NumeroClienteId, FechaDesde, FechaHasta, active,
            MedidorId, EstadoValidacionId, RegionId, EdificioId, NombreOpcional
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}
    else:
        total, items = svc.list(
            db, q, page, page_size,
            DivisionId, ServicioId, EnergeticoId, NumeroClienteId, FechaDesde, FechaHasta, active,
            MedidorId, EstadoValidacionId, RegionId, EdificioId, NombreOpcional
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/{compra_id}", response_model=CompraDTO, summary="Detalle (incluye items por medidor)")
def get_compra(compra_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    c = svc.get(db, compra_id)
    items = svc._items_by_compra(db, compra_id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.get(
    "/{compra_id}/detalle",
    response_model=CompraFullDetalleDTO,
    summary="Detalle enriquecido (compra + items + servicio/institución + región/comuna + dirección + medidores)"
)
def get_compra_detalle(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep
):
    data = svc.get_full(db, compra_id)
    return CompraFullDetalleDTO(**data)


@router.post("", response_model=CompraDTO, status_code=status.HTTP_201_CREATED, summary="(ADMINISTRADOR) Crear compra/consumo")
def create_compra(
    payload: CompraCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]
):
    c, items = svc.create(db, payload, created_by=current_user.id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.put("/{compra_id}", response_model=CompraDTO, summary="(ADMINISTRADOR) Actualizar compra/consumo")
def update_compra(
    compra_id: int,
    payload: CompraUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]
):
    c, items = svc.update(db, compra_id, payload, modified_by=current_user.id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.delete("/{compra_id}", status_code=status.HTTP_204_NO_CONTENT, summary="(ADMINISTRADOR) Eliminar compra/consumo (soft-delete)")
def delete_compra(
    compra_id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]
):
    svc.soft_delete(db, compra_id, modified_by=current_user.id)
    return None


@router.patch("/{compra_id}/reactivar", response_model=CompraDTO, summary="(ADMINISTRADOR) Reactivar compra/consumo")
def reactivate_compra(
    compra_id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]
):
    c = svc.reactivate(db, compra_id, modified_by=current_user.id)
    items = svc._items_by_compra(db, compra_id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.put("/{compra_id}/medidores", response_model=List[CompraMedidorItemDTO], summary="(ADMINISTRADOR) Reemplaza los items de medidor para la compra")
def replace_items_compra(
    compra_id: int,
    payload: CompraItemsPayload,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]
):
    rows = svc.replace_items(db, compra_id, [x.model_dump() for x in (payload.Items or [])])
    return [CompraMedidorItemDTO.model_validate(x) for x in rows]
