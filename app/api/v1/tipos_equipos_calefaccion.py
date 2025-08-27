# app/api/v1/tipos_equipos_calefaccion.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.tipo_equipo_calefaccion import (
    TipoEquipoCalefaccionDTO, TipoEquipoCalefaccionSelectDTO,
    TipoEquipoCalefaccionCreate, TipoEquipoCalefaccionUpdate,
    TECEnergeticoDTO, TECEnergeticoCreate
)
from app.services.tipo_equipo_calefaccion_service import TipoEquipoCalefaccionService

router = APIRouter(prefix="/api/v1/tipos-equipos-calefaccion", tags=["Tipos de equipos de calefacción"])
svc = TipoEquipoCalefaccionService()
DbDep = Annotated[Session, Depends(get_db)]

# ------- Catálogo -------
@router.get("", response_model=dict)
def list_tipos(
    db: DbDep,
    q: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return svc.list(db, q, page, page_size)

@router.get("/select", response_model=List[TipoEquipoCalefaccionSelectDTO])
def select_tipos(
    db: DbDep,
    q: str | None = Query(default=None),
):
    rows = svc.list_select(db, q)
    return [TipoEquipoCalefaccionSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]

@router.get("/{id}", response_model=TipoEquipoCalefaccionDTO)
def get_tipo(
    db: DbDep,
    id: Annotated[int, Path(..., ge=1)],
):
    return svc.get(db, id)

@router.post("", response_model=TipoEquipoCalefaccionDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear tipo de equipo de calefacción")
def create_tipo(
    payload: TipoEquipoCalefaccionCreate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.create(db, payload)

@router.put("/{id}", response_model=TipoEquipoCalefaccionDTO,
            summary="(ADMINISTRADOR) Actualizar tipo de equipo de calefacción")
def update_tipo(
    id: int,
    payload: TipoEquipoCalefaccionUpdate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.update(db, id, payload)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar tipo de equipo de calefacción")
def delete_tipo(
    id: int,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, id)
    return None

# ------- N:M con Energéticos -------
@router.get("/{tipo_id}/energeticos", response_model=List[TECEnergeticoDTO])
def list_relaciones(
    tipo_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    rows = svc.list_rel(db, tipo_id)
    return [TECEnergeticoDTO.model_validate(x) for x in rows]

@router.post("/{tipo_id}/energeticos", response_model=TECEnergeticoDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Vincular energético a tipo de equipo de calefacción")
def add_relacion(
    tipo_id: Annotated[int, Path(..., ge=1)],
    payload: TECEnergeticoCreate,
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    rel = svc.add_rel(db, tipo_id, payload.EnergeticoId)
    return TECEnergeticoDTO.model_validate(rel)

@router.delete("/energeticos/{rel_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar relación tipo-energético")
def delete_relacion(
    rel_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    _user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete_rel(db, rel_id)
    return None
