from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Path, status, Response
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.catalogo_simple import CatalogoDTO, CatalogoPage, CatalogoUpdate
from app.schemas.tipo_colector import (
    TipoColectorDTO,
    TipoColectorCreate,
    TipoColectorUpdate,
    TipoColectorListDTO,
)
from app.services.tipo_colector_service import TipoColectorService

router = APIRouter(prefix="/api/v1/tipos-colectores", tags=["Tipos de colectores"])
DbDep = Annotated[Session, Depends(get_db)]
svc = TipoColectorService()

# Listado paginado (devuelve CatalogoDTO para compatibilidad con grillas simples)
@router.get("", response_model=CatalogoPage, summary="Listar (paginado)")
def list_(db: DbDep, q: str | None = Query(None), page: int = 1, page_size: int = 50):
    q = q.strip() if isinstance(q, str) else q
    data = svc.list(db, q, page, page_size)
    return {
        "total": data["total"],
        "page": data["page"],
        "page_size": data["page_size"],
        "items": [CatalogoDTO.model_validate(x) for x in data["items"]],
    }

@router.get("/{id}", response_model=TipoColectorDTO, summary="Obtener por Id (detalle)")
def get_(db: DbDep, id: Annotated[int, Path(..., ge=1)]):
    return TipoColectorDTO.model_validate(svc.get(db, id))

# POST: admite que el front solo envíe Nombre; lo demás queda en 0/True
@router.post("", response_model=TipoColectorDTO, status_code=status.HTTP_201_CREATED, summary="(ADMIN) Crear")
def create_(payload: TipoColectorCreate, db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = svc.create(db, payload, user=getattr(u, "Username", None))
    return TipoColectorDTO.model_validate(obj)

# PUT genérico (Nombre/Active)
@router.put("/{id}", response_model=TipoColectorDTO, summary="(ADMIN) Actualizar")
def update_(id: Annotated[int, Path(..., ge=1)], payload: CatalogoUpdate, db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = svc.update(db, id, payload, user=getattr(u, "Username", None))
    return TipoColectorDTO.model_validate(obj)

# PATCH parcial (cualquier campo)
@router.patch("/{id}", response_model=TipoColectorDTO, summary="(ADMIN) Actualizar (parcial)")
def patch_(id: Annotated[int, Path(..., ge=1)], payload: TipoColectorUpdate, db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    obj = svc.update_fields(db, id, payload, user=getattr(u, "Username", None))
    return TipoColectorDTO.model_validate(obj)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="(ADMIN) Eliminar")
def delete_(id: Annotated[int, Path(..., ge=1)], db: DbDep, u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    svc.delete(db, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
