# app/api/routes/compras.py
from __future__ import annotations
from typing import Annotated, List, Union, Optional

from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.compra import (
    CompraDTO, CompraCreate, CompraUpdate,
    CompraMedidorItemDTO, CompraItemsPayload,
    CompraPage, CompraFullPage, CompraFullDetalleDTO
)
from app.services.compra_service import CompraService

router = APIRouter(prefix="/api/v1/compras", tags=["Compras / Consumos"])
DbDep = Annotated[Session, Depends(get_db)]
svc = CompraService()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers locales (no tocan esquema ni modelos)
# ─────────────────────────────────────────────────────────────────────────────
_MAX_PAGE_SIZE = 100

def _clamp_page(n: int) -> int:
    return 1 if n < 1 else n

def _clamp_page_size(n: int) -> int:
    if n < 1:
        return 10
    if n > _MAX_PAGE_SIZE:
        return _MAX_PAGE_SIZE
    return n

def _nz_str(s: Optional[str]) -> Optional[str]:
    """Devuelve None si la cadena viene vacía/espacios."""
    if s is None:
        return None
    s2 = s.strip()
    return s2 if s2 else None

def _validate_dates(desde: Optional[str], hasta: Optional[str]) -> None:
    """Valida solamente orden lógico si ambas vienen (sin parse complejo)."""
    if not desde or not hasta:
        return
    # Comparamos string YYYY-MM-DD/ISO por orden lexicográfico suficiente
    if len(desde) >= 10 and len(hasta) >= 10 and desde[:10] > hasta[:10]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FechaDesde no puede ser mayor que FechaHasta."
        )

# ─────────────────────────────────────────────────────────────────────────────
# Rutas
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    summary="Listado paginado de compras/consumos (básico o enriquecido)",
    response_model=Union[CompraFullPage, CompraPage]
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
    """
    Si full=True: usa el get_full por cada fila (sin cambiar el servicio ni el esquema).
    Si full=False: devuelve el listado básico tal como lo tienes hoy.
    """
    if not full:
        # === Básico (sin Items/Direccion) ===
        total, items = svc.list(
            db, q, page, page_size,
            DivisionId=DivisionId, ServicioId=ServicioId, EnergeticoId=EnergeticoId, NumeroClienteId=NumeroClienteId,
            FechaDesde=FechaDesde, FechaHasta=FechaHasta, active=active,
            MedidorId=MedidorId, EstadoValidacionId=EstadoValidacionId, RegionId=RegionId, EdificioId=EdificioId,
            NombreOpcional=NombreOpcional, full=False
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    # === Enriquecido (Items, MedidorIds, Direccion, etc.) usando get_full() por fila ===
    # 1) Primero pedimos la página básica sólo para obtener los IDs de esa página.
    total, items_basic = svc.list(
        db, q, page, page_size,
        DivisionId=DivisionId, ServicioId=ServicioId, EnergeticoId=EnergeticoId, NumeroClienteId=NumeroClienteId,
        FechaDesde=FechaDesde, FechaHasta=FechaHasta, active=active,
        MedidorId=MedidorId, EstadoValidacionId=EstadoValidacionId, RegionId=RegionId, EdificioId=EdificioId,
        NombreOpcional=NombreOpcional, full=False
    )

    # 2) Por cada Id, traemos el detalle enriquecido con el método que YA funciona.
    full_items = []
    for it in items_basic:
        cid = it.get("Id")
        if cid is None:
            continue
        full_items.append(svc.get_full(db, cid))

    return {"total": total, "page": page, "page_size": page_size, "items": full_items}


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
    rows = svc.replace_items(db, compra_id, [x.model_dump() for x in (payload.Items or [])])
    return [CompraMedidorItemDTO.model_validate(x) for x in rows]
