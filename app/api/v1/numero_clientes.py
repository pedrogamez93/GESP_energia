from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.numero_cliente import (
    NumeroClienteDTO,
    NumeroClienteListDTO,
    NumeroClienteCreate,
    NumeroClienteUpdate,
    NumeroClientePage,
    NumeroClienteDetalleDTO,
)
from app.services.numero_cliente_service import NumeroClienteService

router = APIRouter(prefix="/api/v1/numero-clientes", tags=["NúmeroClientes"])
svc = NumeroClienteService()
DbDep = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=NumeroClientePage,
    summary="Listado paginado de número de clientes",
)
def list_numero_clientes(
    db: DbDep,
    q: str | None = Query(default=None, description="Busca en Nº/NombreCliente"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    EmpresaDistribuidoraId: int | None = Query(default=None),
    TipoTarifaId: int | None = Query(default=None),
    DivisionId: int | None = Query(default=None),
    active: bool | None = Query(default=True),
):
    return svc.list(
        db, q, page, page_size,
        EmpresaDistribuidoraId, TipoTarifaId, DivisionId, active
    )


@router.get("/{num_cliente_id}", response_model=NumeroClienteDTO, summary="Detalle (básico)")
def get_numero_cliente(
    num_cliente_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.get(db, num_cliente_id)


@router.get(
    "/{num_cliente_id}/detalle",
    response_model=NumeroClienteDetalleDTO,
    summary="Detalle enriquecido (servicio, institución, región y dirección)"
)
def get_numero_cliente_detalle(
    num_cliente_id: Annotated[int, Path(..., ge=1)],
    db: DbDep
):
    data = svc.detalle(db, num_cliente_id)
    return NumeroClienteDetalleDTO(**data)


@router.post(
    "",
    response_model=NumeroClienteDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMINISTRADOR) Crear número de cliente"
)
def create_numero_cliente(
    payload: NumeroClienteCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.create(db, payload, created_by=current_user.id)


@router.put(
    "/{num_cliente_id}",
    response_model=NumeroClienteDTO,
    summary="(ADMINISTRADOR) Actualizar número de cliente"
)
def update_numero_cliente(
    num_cliente_id: int,
    payload: NumeroClienteUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.update(db, num_cliente_id, payload, modified_by=current_user.id)


@router.delete(
    "/{num_cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMINISTRADOR) Eliminar número de cliente (soft-delete)"
)
def delete_numero_cliente(
    num_cliente_id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.soft_delete(db, num_cliente_id, modified_by=current_user.id)
    return None


@router.patch(
    "/{num_cliente_id}/reactivar",
    response_model=NumeroClienteDTO,
    summary="(ADMINISTRADOR) Reactivar número de cliente"
)
def reactivate_numero_cliente(
    num_cliente_id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.reactivate(db, num_cliente_id, modified_by=current_user.id)
