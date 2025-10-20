# app/api/v1/tipos_equipos_calefaccion.py
from __future__ import annotations
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query, Path, status, Response
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.catalogo_simple import CatalogoDTO, CatalogoCreate, CatalogoUpdate
from app.schemas.tipo_equipo_calefaccion import TECEnergeticoDTO, TECEnergeticoCreate, TECEnergeticoListDTO
from app.services.tipo_equipo_calefaccion_service import TipoEquipoCalefaccionService

router = APIRouter(prefix="/api/v1/tipos-equipos-calefaccion", tags=["Tipos Equipos Calefacción"])
DbDep = Annotated[Session, Depends(get_db)]
svc = TipoEquipoCalefaccionService()

# -------- CRUD catálogo --------
@router.get("", response_model=dict, summary="Listar (paginado)")
def list_(db: DbDep, q: str | None = Query(None), page: int = 1, page_size: int = 50):
    q = q.strip() if isinstance(q, str) else q
    return svc.list(db, q, page, page_size)

@router.get("/{id}", response_model=CatalogoDTO, summary="Obtener por Id")
def get_(db: DbDep, id: Annotated[int, Path(..., ge=1)]):
    return CatalogoDTO.model_validate(svc.get(db, id))

@router.post("", response_model=CatalogoDTO, status_code=status.HTTP_201_CREATED, summary="(ADMIN) Crear")
def create_(payload: CatalogoCreate, db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = svc.create(db, payload, user=getattr(u, "Username", None))
    return CatalogoDTO.model_validate(obj)

@router.put("/{id}", response_model=CatalogoDTO, summary="(ADMIN) Actualizar")
def update_(id: Annotated[int, Path(..., ge=1)], payload: CatalogoUpdate, db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = svc.update(db, id, payload, user=getattr(u, "Username", None))
    return CatalogoDTO.model_validate(obj)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="(ADMIN) Eliminar")
def delete_(id: Annotated[int, Path(..., ge=1)], db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    svc.delete(db, id); return Response(status_code=status.HTTP_204_NO_CONTENT)

# -------- Compatibilidades equipo ↔ energético --------
@router.get("/{id}/compat", response_model=TECEnergeticoListDTO, summary="Listar compatibilidades del equipo")
def list_rel_(id: Annotated[int, Path(..., ge=1)], db: DbDep):
    rows = svc.list_rel(db, id)
    return TECEnergeticoListDTO(Items=[TECEnergeticoDTO.model_validate(x) for x in rows])

@router.post("/{id}/compat", response_model=TECEnergeticoDTO, status_code=status.HTTP_201_CREATED, summary="Agregar compatibilidad")
def add_rel_(id: Annotated[int, Path(..., ge=1)], payload: TECEnergeticoCreate, db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = svc.add_rel(db, id, payload.EnergeticoId)
    return TECEnergeticoDTO.model_validate(obj)

@router.delete("/{id}/compat/{rel_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar compatibilidad")
def del_rel_(id: Annotated[int, Path(..., ge=1)], rel_id: Annotated[int, Path(..., ge=1)], db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    svc.delete_rel(db, rel_id); return Response(status_code=status.HTTP_204_NO_CONTENT)
