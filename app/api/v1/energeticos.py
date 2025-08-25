from typing import Annotated
from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.energetico import (
    EnergeticoDTO, EnergeticoListDTO, EnergeticoCreate, EnergeticoUpdate, EnergeticoSelectDTO,
    EnergeticoUMDTO, EnergeticoUMCreate, EnergeticoUMUpdate, EnergeticoDivisionDTO,
)
from app.services.energetico_service import EnergeticoService

router = APIRouter(prefix="/api/v1/energeticos", tags=["Energéticos"])
svc = EnergeticoService()
DbDep = Annotated[Session, Depends(get_db)]

# ---------- GET públicos ----------
@router.get("", response_model=dict)
def list_energeticos(
    db: DbDep,
    q: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return svc.list(db, q, page, page_size)

@router.get("/select", response_model=list[EnergeticoSelectDTO])
def list_energeticos_select(db: DbDep):
    rows = svc.list_select(db)
    return [EnergeticoSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]

@router.get("/{id}", response_model=EnergeticoDTO)
def get_energetico(
    db: DbDep,
    id: Annotated[int, Path(..., ge=1)],
):
    return svc.get(db, id)

# Energeticos por división (equivale a GetByDivisionId)
@router.get("/division/{division_id}", response_model=list[EnergeticoDivisionDTO])
def get_by_division(
    db: DbDep,
    division_id: Annotated[int, Path(..., ge=1)],
):
    rows = svc.by_division(db, division_id)
    return rows

# Activos por división (equivale a GetEnergeticosActivos) – pendiente validar permiso de compra
@router.get("/activos/division/{division_id}", response_model=list[EnergeticoDTO])
def get_activos_by_division(
    db: DbDep,
    division_id: Annotated[int, Path(..., ge=1)],
):
    items = svc.activos_by_division(db, division_id)
    return items

# Equivalente a GetByEdificioId – dejamos 501 hasta tener los modelos/tablas asociados
@router.get("/edificio/{edificio_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def get_by_edificio(
    db: DbDep,
    edificio_id: Annotated[int, Path(..., ge=1)],
):
    raise HTTPException(status_code=501, detail="Pendiente implementar (requiere modelo/tabla de Edificio y relación)")

# ---------- Escrituras ADMINISTRADOR ----------
@router.post("", response_model=EnergeticoDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear energético")
def create_energetico(
    payload: EnergeticoCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.create(db, payload)

@router.put("/{id}", response_model=EnergeticoDTO,
            summary="(ADMINISTRADOR) Actualizar energético")
def update_energetico(
    id: int,
    payload: EnergeticoUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.update(db, id, payload)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar energético (hard delete)")
def delete_energetico(
    id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, id)
    return None

# ---------- Unidades de medida por energético (N:M con metadata) ----------
@router.get("/{energetico_id}/unidades-medida", response_model=list[EnergeticoUMDTO])
def list_um(
    energetico_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.list_um(db, energetico_id)

@router.post("/{energetico_id}/unidades-medida", response_model=EnergeticoUMDTO,
             status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Agregar unidad de medida a un energético")
def add_um(
    energetico_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoUMCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.add_um(db, energetico_id, payload)

@router.put("/um/{um_id}", response_model=EnergeticoUMDTO,
            summary="(ADMINISTRADOR) Actualizar relación UM de un energético")
def update_um(
    um_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoUMUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.update_um(db, um_id, payload)

@router.delete("/um/{um_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar relación UM de un energético")
def delete_um(
    um_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete_um(db, um_id)
    return None
