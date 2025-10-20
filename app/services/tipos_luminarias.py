# app/api/v1/tipos_luminarias.py
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Path, status, Response
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.catalogo_simple import CatalogoDTO, CatalogoCreate, CatalogoUpdate
from app.services.tipo_luminaria_service import TipoLuminariaService

router = APIRouter(prefix="/api/v1/tipos-luminarias", tags=["Tipos Luminarias"])
DbDep = Annotated[Session, Depends(get_db)]
svc = TipoLuminariaService()

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
    svc.delete(db, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
