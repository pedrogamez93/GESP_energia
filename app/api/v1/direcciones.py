from __future__ import annotations
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.direcciones import (
    DireccionDTO, DireccionCreate, DireccionUpdate, DireccionSearchResponse, DireccionResolveRequest
)
from app.services.direccion_service import DireccionService
from app.core.security import require_roles
from app.schemas.auth import UserPublic

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/api/v1/direcciones", tags=["Direcciones"])

@router.get("", response_model=List[DireccionDTO], summary="Listado paginado/filtrado de direcciones")
def listar_direcciones(
    response: Response,
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    region_id: Annotated[int | None, Query()] = None,
    provincia_id: Annotated[int | None, Query()] = None,
    comuna_id: Annotated[int | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
):
    total, items = DireccionService(db).list_paged(
        page=page, page_size=page_size,
        region_id=region_id, provincia_id=provincia_id, comuna_id=comuna_id, search=search
    )
    total_pages = (total + page_size - 1) // page_size if page_size else 1
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Total-Pages"] = str(total_pages)
    return [DireccionDTO.model_validate(x) for x in items]

@router.get("/{direccion_id}", response_model=DireccionDTO, summary="Detalle dirección")
def obtener_direccion(
    direccion_id: Annotated[int, Path(ge=1)],
    db: DbDep,
):
    obj = DireccionService(db).get(direccion_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrada")
    return DireccionDTO.model_validate(obj)

@router.post("", response_model=DireccionDTO, status_code=status.HTTP_201_CREATED, summary="(ADMIN) Crear dirección")
def crear_direccion(
    data: DireccionCreate,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    created = DireccionService(db).create(data)
    return DireccionDTO.model_validate(created)

@router.put("/{direccion_id}", response_model=DireccionDTO, summary="(ADMIN) Actualizar dirección")
def actualizar_direccion(
    direccion_id: Annotated[int, Path(ge=1)],
    data: DireccionUpdate,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    updated = DireccionService(db).update(direccion_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrada")
    return DireccionDTO.model_validate(updated)

@router.delete("/{direccion_id}", status_code=status.HTTP_204_NO_CONTENT, summary="(ADMIN) Eliminar dirección")
def eliminar_direccion(
    direccion_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    ok = DireccionService(db).delete(direccion_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Compat .NET: resolver dirección exacta
@router.post("/resolve", response_model=DireccionDTO | None, summary="Resolver dirección exacta (calle/numero/comuna)")
def resolver_direccion(
    body: DireccionResolveRequest,
    db: DbDep,
):
    obj = DireccionService(db).resolve_exact(body.Calle, body.Numero, body.ComunaId)
    return DireccionDTO.model_validate(obj) if obj else None
