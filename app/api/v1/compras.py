# app/api/routes/compras.py
from __future__ import annotations

from typing import Annotated, List, Union, Optional

from fastapi import APIRouter, Depends, Query, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db

# ✅ Roles
from app.core.security import require_roles
# si agregaste el helper:
# from app.core.security import require_admin_or_gestor_unidad

from app.schemas.auth import UserPublic
from app.schemas.compra import (
    CompraDTO,
    CompraCreate,
    CompraUpdate,
    CompraMedidorItemDTO,
    CompraItemsPayload,
    CompraPage,
    CompraFullPage,
    CompraFullDetalleDTO,
    CompraFullDTO,
    CompraMedidorItemFullDTO,
)

# ✅ Resolver UnidadId -> DivisionId (UnidadesInmuebles.InmuebleId)
from app.services.unidad_scope import division_id_from_unidad
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


# ==========================================================
# LISTADO (con token de cualquier rol, no público)
# ==========================================================
@router.get(
    "",
    summary="Listado paginado de compras/consumos (básico o enriquecido)",
    response_model=Union[CompraFullPage, CompraPage],
    # si quieres que NO sea público:
    dependencies=[Depends(require_roles("*"))],
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
    FechaDesde: str | None = Query(default=None, description="ISO date (YYYY-MM-DD)"),
    FechaHasta: str | None = Query(default=None, description="ISO date (YYYY-MM-DD) — inclusiva"),
    active: bool | None = Query(default=True),
    MedidorId: int | None = Query(default=None),
    EstadoValidacionId: str | None = Query(default=None),
    RegionId: int | None = Query(default=None),
    EdificioId: int | None = Query(default=None),

    # ✅ NUEVO: filtro por unidad (alias)
    UnidadId: int | None = Query(default=None, description="Alias: resuelve a DivisionId vía UnidadesInmuebles"),

    NombreOpcional: str | None = Query(default=None, description="Match en c.NombreOpcional o d.Nombre"),
    full: bool = Query(default=True, description="Si true, retorna versión enriquecida"),
):
    page = _clamp_page(page)
    page_size = _clamp_page_size(page_size)

    q = _nz_str(q)
    FechaDesde = _nz_str(FechaDesde)
    FechaHasta = _nz_str(FechaHasta)
    EstadoValidacionId = _nz_str(EstadoValidacionId)
    NombreOpcional = _nz_str(NombreOpcional)

    # ✅ Alias por unidad: UnidadId -> DivisionId (InmuebleId)
    if UnidadId is not None:
        resolved_div = division_id_from_unidad(db, int(UnidadId))

        if DivisionId is not None and int(DivisionId) != int(resolved_div):
            return JSONResponse(
                status_code=400,
                content={
                    "code": "division_mismatch",
                    "msg": "DivisionId no coincide con el inmueble de la unidad",
                    "UnidadId": int(UnidadId),
                    "DivisionId_given": int(DivisionId),
                    "DivisionId_from_unidad": int(resolved_div),
                },
            )

        DivisionId = int(resolved_div)

    if full:
        total, items = svc.list_full(
            db,
            q,
            page,
            page_size,
            division_id=DivisionId,
            servicio_id=ServicioId,
            energetico_id=EnergeticoId,
            numero_cliente_id=NumeroClienteId,
            fecha_desde=FechaDesde,
            fecha_hasta=FechaHasta,
            active=active,
            medidor_id=MedidorId,
            estado_validacion_id=EstadoValidacionId,
            region_id=RegionId,
            edificio_id=EdificioId,
            nombre_opcional=NombreOpcional,
        )
        return JSONResponse(
            content={
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": items,
            }
        )

    result = svc.list(
        db,
        q,
        page,
        page_size,
        DivisionId=DivisionId,
        ServicioId=ServicioId,
        EnergeticoId=EnergeticoId,
        NumeroClienteId=NumeroClienteId,
        FechaDesde=FechaDesde,
        FechaHasta=FechaHasta,
        active=active,
        MedidorId=MedidorId,
        EstadoValidacionId=EstadoValidacionId,
        RegionId=RegionId,
        EdificioId=EdificioId,
        NombreOpcional=NombreOpcional,
        full=False,
    )
    return result


# ==========================================================
# DETALLE (token cualquiera)
# ==========================================================
@router.get(
    "/{compra_id}",
    response_model=CompraFullDTO,
    summary="Detalle (incluye items por medidor + Medidor completo)",
    response_model_exclude_none=True,
    dependencies=[Depends(require_roles("*"))],
)
def get_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    c = svc.get(db, compra_id)
    items = svc._items_by_compra_with_medidor_full(db, compra_id)

    dto = CompraFullDTO.model_validate(c)
    dto.Items = [CompraMedidorItemFullDTO.model_validate(x) for x in items]
    return dto


@router.get(
    "/{compra_id}/detalle",
    response_model=CompraFullDetalleDTO,
    summary="Detalle enriquecido",
    response_model_exclude_none=True,
    dependencies=[Depends(require_roles("*"))],
)
def get_compra_detalle(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    data = svc.get_full(db, compra_id)
    return CompraFullDetalleDTO(**data)


# ==========================================================
# ✅ OPERACIONES: ADMINISTRADOR O GESTOR_UNIDAD
# ==========================================================
def _op_roles():
    # si agregaste helper en security.py:
    # return Depends(require_admin_or_gestor_unidad())
    return Depends(require_roles("ADMINISTRADOR", "GESTOR_UNIDAD"))


@router.post(
    "",
    response_model=CompraDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear compra/consumo (ADMINISTRADOR | GESTOR_UNIDAD)",
    response_model_exclude_none=True,
)
def create_compra(
    payload: CompraCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, _op_roles()],
):
    c, items = svc.create(db, payload, created_by=current_user.id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.put(
    "/{compra_id}",
    response_model=CompraDTO,
    summary="Actualizar compra/consumo (ADMINISTRADOR | GESTOR_UNIDAD)",
    response_model_exclude_none=True,
)
def update_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    payload: CompraUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, _op_roles()],
):
    c, items = svc.update(db, compra_id, payload, modified_by=current_user.id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.delete(
    "/{compra_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar compra/consumo (soft-delete) (ADMINISTRADOR | GESTOR_UNIDAD)",
)
def delete_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, _op_roles()],
):
    svc.soft_delete(db, compra_id, modified_by=current_user.id)
    return None


@router.patch(
    "/{compra_id}/reactivar",
    response_model=CompraDTO,
    summary="Reactivar compra/consumo (ADMINISTRADOR | GESTOR_UNIDAD)",
    response_model_exclude_none=True,
)
def reactivate_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, _op_roles()],
):
    c = svc.reactivate(db, compra_id, modified_by=current_user.id)
    items = svc._items_by_compra(db, compra_id)
    dto = CompraDTO.model_validate(c)
    dto.Items = [CompraMedidorItemDTO.model_validate(x) for x in items]
    return dto


@router.put(
    "/{compra_id}/medidores",
    response_model=List[CompraMedidorItemDTO],
    summary="Reemplaza items de medidor (ADMINISTRADOR | GESTOR_UNIDAD)",
    response_model_exclude_none=True,
)
def replace_items_compra(
    compra_id: Annotated[int, Path(..., ge=1)],
    payload: CompraItemsPayload,
    db: DbDep,
    current_user: Annotated[UserPublic, _op_roles()],
):
    rows = svc.replace_items(
        db,
        compra_id,
        [x.model_dump() for x in (payload.Items or [])],
        modified_by=current_user.id,
    )
    return [CompraMedidorItemDTO.model_validate(x) for x in rows]
