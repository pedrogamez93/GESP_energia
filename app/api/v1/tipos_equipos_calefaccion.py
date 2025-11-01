# app/api/v1/tipos_equipos_calefaccion.py
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Path, status, Response
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

# Reutilizamos tus catálogos ligeros para listar por nombre (UI izquierda)
from app.schemas.catalogo_simple import (
    CatalogoDTO,
    CatalogoCreate,   # <- ya no lo usamos para crear, se deja por compatibilidad de imports
    CatalogoUpdate,   # <- ya no lo usamos para actualizar
    CatalogoPage,
)

# Schemas específicos del recurso (para crear/actualizar con todos los campos)
from app.schemas.tipo_equipo_calefaccion import (
    TECEnergeticoDTO,
    TECEnergeticoCreate,
    TECEnergeticoListDTO,
    TipoEquipoCalefaccionCreate,
    TipoEquipoCalefaccionUpdate,
)

from app.services.tipo_equipo_calefaccion_service import TipoEquipoCalefaccionService


router = APIRouter(prefix="/api/v1/tipos-equipos-calefaccion", tags=["Tipos Equipos Calefacción"])
DbDep = Annotated[Session, Depends(get_db)]
svc = TipoEquipoCalefaccionService()


@router.get("", response_model=CatalogoPage, summary="Listar (paginado)")
def list_(db: DbDep, q: str | None = Query(None), page: int = 1, page_size: int = 50):
    q = q.strip() if isinstance(q, str) else q
    data = svc.list(db, q, page, page_size)
    return {
        "total": data["total"],
        "page": data["page"],
        "page_size": data["page_size"],
        "items": [CatalogoDTO(Id=x.Id, Nombre=x.Nombre) for x in data["items"]],
    }


@router.get("/{id}", response_model=CatalogoDTO, summary="Obtener por Id")
def get_(db: DbDep, id: Annotated[int, Path(..., ge=1)]):
    obj = svc.get(db, id)
    return CatalogoDTO(Id=obj.Id, Nombre=obj.Nombre)


# 🚨 CORRECCIÓN CLAVE:
# Para crear/actualizar usamos los schemas específicos con TODOS los campos,
# evitando que se pierdan al validar (y evitando INSERT con NULL en NOT NULL).
@router.post("", response_model=CatalogoDTO, status_code=status.HTTP_201_CREATED, summary="(ADMIN) Crear")
def create_(
    payload: TipoEquipoCalefaccionCreate,
    db: DbDep,
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.create(db, payload, user=getattr(u, "Username", None))
    return CatalogoDTO(Id=obj.Id, Nombre=obj.Nombre)


@router.put("/{id}", response_model=CatalogoDTO, summary="(ADMIN) Actualizar")
def update_(
    id: Annotated[int, Path(..., ge=1)],
    payload: TipoEquipoCalefaccionUpdate,
    db: DbDep,
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.update(db, id, payload, user=getattr(u, "Username", None))
    return CatalogoDTO(Id=obj.Id, Nombre=obj.Nombre)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="(ADMIN) Eliminar")
def delete_(
    id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -------- Compatibilidades equipo ↔ energético --------
@router.get("/{id}/compat", response_model=TECEnergeticoListDTO, summary="Listar compatibilidades del equipo")
def list_rel_(id: Annotated[int, Path(..., ge=1)], db: DbDep):
    rows = svc.list_rel(db, id)
    return TECEnergeticoListDTO(Items=[TECEnergeticoDTO.model_validate(x) for x in rows])


@router.post("/{id}/compat", response_model=TECEnergeticoDTO, status_code=status.HTTP_201_CREATED, summary="Agregar compatibilidad")
def add_rel_(
    id: Annotated[int, Path(..., ge=1)],
    payload: TECEnergeticoCreate,
    db: DbDep,
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.add_rel(db, id, payload.EnergeticoId)
    return TECEnergeticoDTO.model_validate(obj)


@router.delete("/{id}/compat/{rel_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar compatibilidad")
def del_rel_(
    id: Annotated[int, Path(..., ge=1)],
    rel_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete_rel(db, rel_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
