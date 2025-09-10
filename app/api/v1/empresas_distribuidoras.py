from __future__ import annotations
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.empresa_distribuidora import (
    EmpresaDistribuidoraDTO,
    EmpresaDistribuidoraDetailDTO,
    EmpresaDistribuidoraCreate,
    EmpresaDistribuidoraUpdate,
    EmpresaDistribuidoraSelectDTO,
    EmpresaDistribuidoraListDTO,
)
from app.services.empresa_distribuidora_service import EmpresaDistribuidoraService

router = APIRouter(prefix="/api/v1/empresas-distribuidoras", tags=["Empresas distribuidoras"])
svc = EmpresaDistribuidoraService()
DbDep = Annotated[Session, Depends(get_db)]

# -------- GET públicos --------
@router.get("", response_model=EmpresaDistribuidoraListDTO, summary="Listar empresas distribuidoras")
def list_empresas(
    db: DbDep,
    q: str | None = Query(default=None, description="Filtro por nombre o RUT (opcional)"),
    page: int = Query(1, ge=1, description="Número de página (mínimo 1)"),
    page_size: int = Query(50, ge=1, le=200, description="Registros por página (1–200)"),
    EnergeticoId: int | None = Query(default=None, description="Id de energético (opcional)"),
    ComunaId: int | None = Query(default=None, description="Id de comuna (opcional)"),
    active: bool | None = Query(default=True, description="Filtrar por estado activo (opcional)"),
):
    res = svc.list(db, q, page, page_size, EnergeticoId, ComunaId, active)
    return EmpresaDistribuidoraListDTO(
        total=res["total"],
        data=[EmpresaDistribuidoraDTO.model_validate(it) for it in res["data"]],
    )

@router.get("/select", response_model=List[EmpresaDistribuidoraSelectDTO], summary="Opciones para select")
def select_empresas(
    db: DbDep,
    EnergeticoId: int | None = Query(default=None, description="Id de energético (opcional)"),
):
    rows = svc.list_select(db, EnergeticoId) or []
    return [EmpresaDistribuidoraSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]

@router.get("/{id}", response_model=EmpresaDistribuidoraDetailDTO, summary="Obtener empresa por Id")
def get_empresa(
    db: DbDep,
    id: Annotated[int, Path(..., ge=1)],
):
    ed, comuna_ids = svc.get_detail(db, id)
    return EmpresaDistribuidoraDetailDTO(
        Id=ed.Id,
        Nombre=ed.Nombre,
        RUT=ed.RUT,
        EnergeticoId=ed.EnergeticoId,
        Active=ed.Active,
        ComunaIds=list(comuna_ids),
    )

# -------- Escrituras (ADMINISTRADOR) --------
@router.post(
    "",
    response_model=EmpresaDistribuidoraDetailDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMINISTRADOR) Crear empresa distribuidora",
)
def create_empresa(
    payload: EmpresaDistribuidoraCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    ed = svc.create(db, payload, created_by=current_user.id)
    # Reusar construcción del detalle
    return get_empresa(db, ed.Id)

@router.put(
    "/{id}",
    response_model=EmpresaDistribuidoraDetailDTO,
    summary="(ADMINISTRADOR) Actualizar empresa distribuidora",
)
def update_empresa(
    id: int,
    payload: EmpresaDistribuidoraUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.update(db, id, payload, modified_by=current_user.id)
    return get_empresa(db, id)

@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMINISTRADOR) Eliminar empresa distribuidora (soft-delete)",
)
def delete_empresa(
    id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.soft_delete(db, id, modified_by=current_user.id)
    return None

@router.patch(
    "/{id}/reactivar",
    response_model=EmpresaDistribuidoraDetailDTO,
    summary="(ADMINISTRADOR) Reactivar empresa distribuidora",
)
def reactivate_empresa(
    id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.reactivate(db, id, modified_by=current_user.id)
    return get_empresa(db, id)

# -------- Set de comunas (opcional, explícito) --------
@router.put(
    "/{id}/comunas",
    response_model=List[int],
    summary="(ADMINISTRADOR) Reemplaza comunas asociadas a la empresa",
)
def set_comunas_empresa(
    id: int,
    comuna_ids: List[int],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.set_comunas(db, id, comuna_ids)
