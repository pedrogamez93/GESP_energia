# app/api/v1/energeticos.py
from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Path, status, Response
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.energetico import (
    EnergeticoDTO, EnergeticoCreate, EnergeticoUpdate,
    EnergeticoUMDTO, EnergeticoUMCreate, EnergeticoUMUpdate
)
from app.services.energetico_service import EnergeticoService

router = APIRouter(prefix="/api/v1/energeticos", tags=["Energeticos"])
DbDep = Annotated[Session, Depends(get_db)]
svc = EnergeticoService()

# ----- CRUD Energetico -----
@router.get("", response_model=dict, summary="Listar (paginado)")
def list_(db: DbDep, q: str | None = Query(None), page: int = 1, page_size: int = 50):
    q = q.strip() if isinstance(q, str) else q
    return svc.list(db, q, page, page_size)

@router.get("/{id}", response_model=EnergeticoDTO, summary="Obtener por Id")
def get_(db: DbDep, id: Annotated[int, Path(..., ge=1)]):
    return EnergeticoDTO.model_validate(svc.get(db, id))

@router.post("", response_model=EnergeticoDTO, status_code=status.HTTP_201_CREATED, summary="(ADMIN) Crear")
def create_(payload: EnergeticoCreate, db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    return EnergeticoDTO.model_validate(svc.create(db, payload))

@router.put("/{id}", response_model=EnergeticoDTO, summary="(ADMIN) Actualizar")
def update_(id: Annotated[int, Path(..., ge=1)], payload: EnergeticoUpdate, db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    return EnergeticoDTO.model_validate(svc.update(db, id, payload))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="(ADMIN) Eliminar")
def delete_(id: Annotated[int, Path(..., ge=1)], db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    svc.delete(db, id); return Response(status_code=status.HTTP_204_NO_CONTENT)

# ----- Unidades por energético (N:M con metadata) -----
@router.get("/{energetico_id}/unidades", response_model=list[EnergeticoUMDTO], summary="Listar UM por energético")
def list_um(energetico_id: Annotated[int, Path(..., ge=1)], db: DbDep):
    return [EnergeticoUMDTO.model_validate(x) for x in svc.list_um(db, energetico_id)]

@router.post("/{energetico_id}/unidades", response_model=EnergeticoUMDTO, status_code=status.HTTP_201_CREATED, summary="Agregar UM")
def add_um(energetico_id: Annotated[int, Path(..., ge=1)], payload: EnergeticoUMCreate, db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    return EnergeticoUMDTO.model_validate(svc.add_um(db, energetico_id, payload))

@router.put("/unidades/{um_id}", response_model=EnergeticoUMDTO, summary="Actualizar UM")
def upd_um(um_id: Annotated[int, Path(..., ge=1)], payload: EnergeticoUMUpdate, db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    return EnergeticoUMDTO.model_validate(svc.update_um(db, um_id, payload))

@router.delete("/unidades/{um_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar UM")
def del_um(um_id: Annotated[int, Path(..., ge=1)], db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    svc.delete_um(db, um_id); return Response(status_code=status.HTTP_204_NO_CONTENT)
