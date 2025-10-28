# app/api/v1/tipos_luminarias.py
from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

# Ajusta estos imports a tus schemas reales
from app.schemas.tipos_luminaria import (
    TipoLuminariaDTO,
    TipoLuminariaCreate,
    TipoLuminariaUpdate,
)

# Ajusta el nombre del servicio al tuyo real
from app.services.tipos_luminarias_service import TipoLuminariaService

router = APIRouter(prefix="/api/v1/tipos-luminarias", tags=["Tipos - Luminarias"])
DbDep = Annotated[Session, Depends(get_db)]
svc = TipoLuminariaService()

# ---- Listado paginado: devuelve {"total": int, "data": [..]} ----
@router.get("", response_model=dict)
def list_(db: DbDep, q: str | None = Query(None), page: int = 1, page_size: int = 50):
    q = q.strip() if isinstance(q, str) else q
    return svc.list(db, q, page, page_size)

# ---- Obtener por id ----
@router.get("/{id}", response_model=TipoLuminariaDTO)
def get_(id: Annotated[int, Path(ge=1)], db: DbDep):
    return TipoLuminariaDTO.model_validate(svc.get(db, id))

# ---- Crear ----
@router.post("", response_model=TipoLuminariaDTO, status_code=status.HTTP_201_CREATED)
def create_(payload: TipoLuminariaCreate, db: DbDep,
            _u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    return TipoLuminariaDTO.model_validate(svc.create(db, payload))

# ---- Actualizar (completo) con PUT ----
@router.put("/{id}", response_model=TipoLuminariaDTO)
def update_(id: Annotated[int, Path(ge=1)], payload: TipoLuminariaUpdate, db: DbDep,
            _u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    return TipoLuminariaDTO.model_validate(svc.update(db, id, payload))

# ---- Actualizar (parcial) con PATCH: acepta el mismo payload por simplicidad ----
@router.patch("/{id}", response_model=TipoLuminariaDTO)
def patch_(id: Annotated[int, Path(ge=1)], payload: TipoLuminariaUpdate, db: DbDep,
           _u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    # Si más adelante quieres parcial-verdadero, crea un schema con todos los campos opcionales
    return TipoLuminariaDTO.model_validate(svc.update(db, id, payload))

# ---- Eliminar ----
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_(id: Annotated[int, Path(ge=1)], db: DbDep,
            _u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    svc.delete(db, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
