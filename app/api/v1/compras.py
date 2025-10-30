# app/api/routes/compras.py
from __future__ import annotations
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.compra import (
    CompraDTO, CompraListDTO, CompraCreate, CompraUpdate,
    CompraMedidorItemDTO, CompraItemsPayload, CompraPage
)
from app.schemas.compra import CompraFullPage, CompraListFullDTO
from app.schemas.compra import CompraFullDTO
from app.services.compra_service import CompraService

router = APIRouter(prefix="/api/v1/compras", tags=["Compras / Consumos"])
svc = CompraService()
DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=CompraPage, summary="Listado paginado de compras/consumos")
def list_compras(
    db: DbDep,
    q: str | None = Query(default=None, description="Busca en Observacion"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    DivisionId: int | None = Query(default=None),
    ServicioId: int | None = Query(default=None),
    EnergeticoId: int | None = Query(default=None),
    NumeroClienteId: int | None = Query(default=None),
    FechaDesde: str | None = Query(default=None),
    FechaHasta: str | None = Query(default=None),
    active: bool | None = Query(default=True),
    # extras
    MedidorId: int | None = Query(default=None),
    EstadoValidacionId: str | None = Query(default=None),
    RegionId: int | None = Query(default=None),
    EdificioId: int | None = Query(default=None),
    NombreOpcional: str | None = Query(default=None),
):
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


@router.get("/{compra_id}/detalle", response_model=CompraFullDTO,
            summary="Detalle enriquecido (compra + items + servicio/institución + región/edificio + medidores)")
def get_compra_detalle(compra_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    data = svc.get_full(db, compra_id)
    return CompraFullDTO.model_validate(data)


@router.get("/{compra_id}/full", response_model=CompraListFullDTO,
            summary="Detalle enriquecido de compra por Id (incluye institución, servicio, unidad, energético, cliente, medidor, región, edificio, etc.)")
def get_compra_full(compra_id: int, db: DbDep):
    total, items = svc.list_full(
        db, q=None, page=1, page_size=1,
        division_id=None, servicio_id=None, energetico_id=None,
        numero_cliente_id=None, fecha_desde=None, fecha_hasta=None,
        active=None, medidor_id=None, estado_validacion_id=None,
        region_id=None, edificio_id=None, nombre_opcional=None
    )
    result = [x for x in items if x["Id"] == compra_id]
    if not result:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return CompraListFullDTO.model_validate(result[0])


@router.post("", response_model=CompraDTO, status_code=status.HTTP_201_CREATED, summary="(ADMINISTRADOR) Crear compra/consumo")
def create_compra(payload: CompraCreate, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    c, items = svc.create(db, payload, created_by=current_user.id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.put("/{compra_id}", response_model=CompraDTO, summary="(ADMINISTRADOR) Actualizar compra/consumo")
def update_compra(compra_id: int, payload: CompraUpdate, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    c, items = svc.update(db, compra_id, payload, modified_by=current_user.id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.delete("/{compra_id}", status_code=status.HTTP_204_NO_CONTENT, summary="(ADMINISTRADOR) Eliminar compra/consumo (soft-delete)")
def delete_compra(compra_id: int, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    svc.soft_delete(db, compra_id, modified_by=current_user.id)
    return None


@router.patch("/{compra_id}/reactivar", response_model=CompraDTO, summary="(ADMINISTRADOR) Reactivar compra/consumo")
def reactivate_compra(compra_id: int, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    c = svc.reactivate(db, compra_id, modified_by=current_user.id)
    items = svc._items_by_compra(db, compra_id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.put("/{compra_id}/medidores", response_model=List[CompraMedidorItemDTO], summary="(ADMINISTRADOR) Reemplaza los items de medidor para la compra")
def replace_items_compra(compra_id: int, payload: CompraItemsPayload, db: DbDep, current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    rows = svc.replace_items(db, compra_id, [x.model_dump() for x in (payload.Items or [])])
    return [CompraMedidorItemDTO.model_validate(x) for x in rows]


@router.get("/resumen/mensual", response_model=List[dict], summary="Resumen mensual por División/Energético (suma de Consumo y Costo)")
def resumen_mensual(db: DbDep, DivisionId: int = Query(..., ge=1), EnergeticoId: int = Query(..., ge=1), Desde: str = Query(..., description="YYYY-MM-01"), Hasta: str = Query(..., description="YYYY-MM-01 (exclusivo)")):
    return svc.resumen_mensual(db, DivisionId, EnergeticoId, Desde, Hasta)


@router.get("/busqueda", response_model=CompraFullPage, summary="Listado enriquecido para buscador (con institución, servicio, región, edificio, medidores, etc.)")
def list_compras_full(
    db: DbDep,
    q: str | None = Query(default=None, description="Busca en Observacion"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
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
):
    total, items = svc.list_full(
        db, q, page, page_size,
        DivisionId, ServicioId, EnergeticoId, NumeroClienteId, FechaDesde, FechaHasta, active,
        MedidorId, EstadoValidacionId, RegionId, EdificioId, NombreOpcional
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [CompraListFullDTO.model_validate(x) for x in items],
    }
