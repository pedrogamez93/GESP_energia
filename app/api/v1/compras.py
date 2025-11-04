# app/api/routes/compras.py
from __future__ import annotations

from typing import Annotated, List, Union, Optional

from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

# Nota: mantengo tu import en singular como lo pediste
from app.schemas.compra import (
    CompraDTO,
    CompraListDTO,
    CompraCreate,
    CompraUpdate,
    CompraMedidorItemDTO,
    CompraItemsPayload,
    CompraPage,
    CompraFullPage,
    CompraListFullDTO,
    CompraFullDetalleDTO,
)

from app.services.compra_service import CompraService

router = APIRouter(prefix="/api/v1/compras", tags=["Compras / Consumos"])
DbDep = Annotated[Session, Depends(get_db)]
svc = CompraService()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos para compatibilidad del service (list vs list_full)
# ─────────────────────────────────────────────────────────────────────────────
def _list_full_compat(
    db: Session,
    q: Optional[str],
    page: int,
    page_size: int,
    DivisionId: Optional[int],
    ServicioId: Optional[int],
    EnergeticoId: Optional[int],
    NumeroClienteId: Optional[int],
    FechaDesde: Optional[str],
    FechaHasta: Optional[str],
    active: Optional[bool],
    MedidorId: Optional[int],
    EstadoValidacionId: Optional[str],
    RegionId: Optional[int],
    EdificioId: Optional[int],
    NombreOpcional: Optional[str],
):
    """
    Intenta usar svc.list_full(...) si existe; si no, usa svc.list(..., full=True).
    Debe devolver (total, items) para mapear al schema CompraFullPage.
    """
    if hasattr(svc, "list_full"):
        return svc.list_full(
            db, q, page, page_size,
            DivisionId, ServicioId, EnergeticoId, NumeroClienteId,
            FechaDesde, FechaHasta, active,
            MedidorId, EstadoValidacionId, RegionId, EdificioId, NombreOpcional,
        )
    else:
        # svc.list devuelve una página ya armada o una tupla;
        # normalizamos a (total, items)
        page_obj = svc.list(
            db=db, q=q, page=page, page_size=page_size,
            DivisionId=DivisionId, ServicioId=ServicioId, EnergeticoId=EnergeticoId,
            NumeroClienteId=NumeroClienteId, FechaDesde=FechaDesde, FechaHasta=FechaHasta,
            active=active, MedidorId=MedidorId, EstadoValidacionId=EstadoValidacionId,
            RegionId=RegionId, EdificioId=EdificioId, NombreOpcional=NombreOpcional,
            full=True,
        )
        # page_obj puede ser dict o BaseModel — ambos tienen .items/.total
        total = getattr(page_obj, "total", None) or page_obj["total"]
        items = getattr(page_obj, "items", None) or page_obj["items"]
        return total, items


def _list_basic_compat(
    db: Session,
    q: Optional[str],
    page: int,
    page_size: int,
    DivisionId: Optional[int],
    ServicioId: Optional[int],
    EnergeticoId: Optional[int],
    NumeroClienteId: Optional[int],
    FechaDesde: Optional[str],
    FechaHasta: Optional[str],
    active: Optional[bool],
    MedidorId: Optional[int],
    EstadoValidacionId: Optional[str],
    RegionId: Optional[int],
    EdificioId: Optional[int],
    NombreOpcional: Optional[str],
):
    """
    Usa svc.list_full(...) si SOLO tienes ése y soporta full=False; si no, svc.list(..., full=False).
    Normaliza a (total, items) para CompraPage.
    """
    # Preferimos svc.list con full=False (o sin arg)
    if hasattr(svc, "list"):
        page_obj = None
        try:
            page_obj = svc.list(
                db=db, q=q, page=page, page_size=page_size,
                DivisionId=DivisionId, ServicioId=ServicioId, EnergeticoId=EnergeticoId,
                NumeroClienteId=NumeroClienteId, FechaDesde=FechaDesde, FechaHasta=FechaHasta,
                active=active, MedidorId=MedidorId, EstadoValidacionId=EstadoValidacionId,
                RegionId=RegionId, EdificioId=EdificioId, NombreOpcional=NombreOpcional,
                full=False,
            )
        except TypeError:
            # Si tu list no acepta full, lo llamamos sin ese parámetro
            page_obj = svc.list(
                db, q, page, page_size,
                DivisionId, ServicioId, EnergeticoId, NumeroClienteId,
                FechaDesde, FechaHasta, active,
                MedidorId, EstadoValidacionId, RegionId, EdificioId, NombreOpcional,
            )
        total = getattr(page_obj, "total", None) or page_obj["total"]
        items = getattr(page_obj, "items", None) or page_obj["items"]
        return total, items

    # Último recurso: si sólo existiera list_full, lo usamos, pero puede venir “grande”.
    total, items = _list_full_compat(
        db, q, page, page_size,
        DivisionId, ServicioId, EnergeticoId, NumeroClienteId,
        FechaDesde, FechaHasta, active,
        MedidorId, EstadoValidacionId, RegionId, EdificioId, NombreOpcional,
    )
    return total, items


# ─────────────────────────────────────────────────────────────────────────────
# Listado: básico o FULL (toggle `full`)
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "",
    summary="Listado paginado de compras/consumos (básico o enriquecido)",
    response_model=Union[CompraFullPage, CompraPage],
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
    full: bool = Query(default=True, description="Si es true, retorna el payload enriquecido"),
):
    if full:
        total, items = _list_full_compat(
            db, q, page, page_size,
            DivisionId, ServicioId, EnergeticoId, NumeroClienteId,
            FechaDesde, FechaHasta, active,
            MedidorId, EstadoValidacionId, RegionId, EdificioId, NombreOpcional,
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}
    else:
        total, items = _list_basic_compat(
            db, q, page, page_size,
            DivisionId, ServicioId, EnergeticoId, NumeroClienteId,
            FechaDesde, FechaHasta, active,
            MedidorId, EstadoValidacionId, RegionId, EdificioId, NombreOpcional,
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}


# Alias explícito para que Swagger muestre el schema FULL directamente
@router.get(
    "/full",
    response_model=CompraFullPage,
    summary="Listado paginado ENRIQUECIDO de compras/consumos",
)
def list_compras_full(
    db: DbDep,
    q: str | None = Query(default=None),
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
):
    total, items = _list_full_compat(
        db, q, page, page_size,
        DivisionId, ServicioId, EnergeticoId, NumeroClienteId,
        FechaDesde, FechaHasta, active,
        MedidorId, EstadoValidacionId, RegionId, EdificioId, NombreOpcional,
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ─────────────────────────────────────────────────────────────────────────────
# Detalles
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/{compra_id}",
    response_model=CompraDTO,
    summary="Detalle (incluye items por medidor)",
)
def get_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
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
)
def get_compra_detalle(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    data = svc.get_full(db, compra_id)
    return CompraFullDetalleDTO(**data)


# ─────────────────────────────────────────────────────────────────────────────
# Escritura (ADMINISTRADOR)
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "",
    response_model=CompraDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMINISTRADOR) Crear compra/consumo",
)
def create_compra(
    payload: CompraCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    c, items = svc.create(db, payload, created_by=current_user.id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.put(
    "/{compra_id}",
    response_model=CompraDTO,
    summary="(ADMINISTRADOR) Actualizar compra/consumo",
)
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


@router.delete(
    "/{compra_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMINISTRADOR) Eliminar compra/consumo (soft-delete)",
)
def delete_compra(
    compra_id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.soft_delete(db, compra_id, modified_by=current_user.id)
    return None


@router.patch(
    "/{compra_id}/reactivar",
    response_model=CompraDTO,
    summary="(ADMINISTRADOR) Reactivar compra/consumo",
)
def reactivate_compra(
    compra_id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
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
)
def replace_items_compra(
    compra_id: int,
    payload: CompraItemsPayload,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    rows = svc.replace_items(db, compra_id, [x.model_dump() for x in (payload.Items or [])])
    return [CompraMedidorItemDTO.model_validate(x) for x in rows]
