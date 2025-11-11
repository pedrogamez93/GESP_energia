# app/api/routes/compras.py
from __future__ import annotations
from typing import Annotated, List, Union, Optional

from fastapi import APIRouter, Depends, Query, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

# 👇 Import corregido (plural)
from app.schemas.compra import (
    CompraDTO, CompraCreate, CompraUpdate,
    CompraMedidorItemDTO, CompraItemsPayload,
    CompraPage, CompraFullPage, CompraFullDetalleDTO
)

from app.services.compra_service import CompraService

router = APIRouter(prefix="/api/v1/compras", tags=["Compras / Consumos"])
DbDep = Annotated[Session, Depends(get_db)]
svc = CompraService()

_MAX_PAGE_SIZE = 200


def _clamp_page(n: int) -> int:
    return 1 if n < 1 else n


def _clamp_page_size(n: int) -> int:
    if n < 1:
        return 10
    if n > _MAX_PAGE_SIZE:
        return _MAX_PAGE_SIZE
    return n


def _nz_str(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s2 = s.strip()
    return s2 if s2 else None


@router.get(
    "",
    summary="Listado paginado de compras/consumos (básico o enriquecido)",
    response_model=Union[CompraFullPage, CompraPage]
)
def list_compras(
    db: DbDep,
    q: str | None = Query(default=None, description="Busca en Observacion"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=_MAX_PAGE_SIZE),
    DivisionId: int | None = Query(default=None),
    ServicioId: int | None = Query(default=None),
    EnergeticoId: int | None = Query(default=None),
    NumeroClienteId: int | None = Query(default=None),
    # Nota: el service trata FechaHasta como inclusiva (convierte a < día_siguiente)
    FechaDesde: str | None = Query(default=None, description="ISO date (YYYY-MM-DD)"),
    FechaHasta: str | None = Query(default=None, description="ISO date (YYYY-MM-DD) — inclusiva"),
    active: bool | None = Query(default=True),
    MedidorId: int | None = Query(default=None),
    EstadoValidacionId: str | None = Query(default=None),
    RegionId: int | None = Query(default=None),
    EdificioId: int | None = Query(default=None),
    NombreOpcional: str | None = Query(default=None, description="Match en c.NombreOpcional o d.Nombre"),
    full: bool = Query(default=True, description="Si true, retorna versión enriquecida"),
):
    # Blindaje adicional (además de Query) por si se llama internamente o cambia el límite
    page = _clamp_page(page)
    page_size = _clamp_page_size(page_size)

    # Normaliza strings (evita búsquedas con espacios vacíos)
    q = _nz_str(q)
    FechaDesde = _nz_str(FechaDesde)
    FechaHasta = _nz_str(FechaHasta)
    EstadoValidacionId = _nz_str(EstadoValidacionId)
    NombreOpcional = _nz_str(NombreOpcional)

    if full:
        # ===== Enriquecido: usa el batch del service y evita que Pydantic pode =====
        total, items = svc.list_full(
            db, q, page, page_size,
            division_id=DivisionId,
            servicio_id=ServicioId,
            energetico_id=EnergeticoId,
            numero_cliente_id=NumeroClienteId,
            fecha_desde=FechaDesde,
            fecha_hasta=FechaHasta,  # inclusiva dentro del service
            active=active,
            medidor_id=MedidorId,
            estado_validacion_id=EstadoValidacionId,
            region_id=RegionId,
            edificio_id=EdificioId,
            nombre_opcional=NombreOpcional,
        )
        # JSONResponse bypass => entrega TODO tal cual (Servicio/Institución/MedidorIds/Items/Dirección/etc.)
        return JSONResponse(content={
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        })

    # ===== Básico: el service ya retorna el dict con total/page/page_size/items =====
    result = svc.list(
        db, q, page, page_size,
        DivisionId=DivisionId, ServicioId=ServicioId, EnergeticoId=EnergeticoId, NumeroClienteId=NumeroClienteId,
        FechaDesde=FechaDesde, FechaHasta=FechaHasta, active=active,
        MedidorId=MedidorId, EstadoValidacionId=EstadoValidacionId, RegionId=RegionId, EdificioId=EdificioId,
        NombreOpcional=NombreOpcional, full=False
    )
    return result


@router.get(
    "/{compra_id}",
    response_model=CompraDTO,
    summary="Detalle (incluye items por medidor)",
    response_model_exclude_none=True,
)
def get_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep
):
    c = svc.get(db, compra_id)
    items = svc._items_by_compra(db, compra_id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.get(
    "/{compra_id}/detalle",
    response_model=CompraFullDetalleDTO,
    summary="Detalle enriquecido (compra + items + servicio/institución + región/comuna + dirección + medidores)",
    response_model_exclude_none=True,
)
def get_compra_detalle(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep
):
    data = svc.get_full(db, compra_id)
    return CompraFullDetalleDTO(**data)


@router.post(
    "",
    response_model=CompraDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMINISTRADOR) Crear compra/consumo",
    response_model_exclude_none=True,
)
def create_compra(
    payload: CompraCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]
):
    c, items = svc.create(db, payload, created_by=current_user.id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.put(
    "/{compra_id}",
    response_model=CompraDTO,
    summary="(ADMINISTRADOR) Actualizar compra/consumo",
    response_model_exclude_none=True,
)
def update_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    payload: CompraUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]
):
    c, items = svc.update(db, compra_id, payload, modified_by=current_user.id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.delete(
    "/{compra_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMINISTRADOR) Eliminar compra/consumo (soft-delete)",
)
def delete_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]
):
    svc.soft_delete(db, compra_id, modified_by=current_user.id)
    return None


@router.patch(
    "/{compra_id}/reactivar",
    response_model=CompraDTO,
    summary="(ADMINISTRADOR) Reactivar compra/consumo",
    response_model_exclude_none=True,
)
def reactivate_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]
):
    c = svc.reactivate(db, compra_id, modified_by=current_user.id)
    items = svc._items_by_compra(db, compra_id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.put(
    "/{compra_id}/medidores",
    response_model=List[CompraMedidorItemDTO],
    summary="(ADMINISTRADOR) Reemplaza los items de medidor para la compra",
    response_model_exclude_none=True,
)
def replace_items_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    payload: CompraItemsPayload,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]
):
    # Permite limpiar items si viene Items=[]
    rows = svc.replace_items(db, compra_id, [x.model_dump() for x in (payload.Items or [])])
    return [CompraMedidorItemDTO.model_validate(x) for x in rows]
