from __future__ import annotations
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query, Path, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.catalogo_simple import (
    CatalogoDTO,
    CatalogoSelectDTO,
    CatalogoCreate,
    CatalogoUpdate,
)
from app.services.sistema_service import SistemaService

router = APIRouter(prefix="/api/v1/sistemas", tags=["Sistemas"])
DbDep = Annotated[Session, Depends(get_db)]
svc = SistemaService()


@router.get(
    "",
    response_model=dict,
    operation_id="sistemas_list_v1",
    summary="Listar sistemas (paginado)",
)
def list_items(
    db: DbDep,
    q: str | None = Query(None, description="Filtro por nombre (contiene)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = q.strip() if isinstance(q, str) else q
    return svc.list(db, q, page, page_size)


@router.get(
    "/select",
    response_model=List[CatalogoSelectDTO],
    operation_id="sistemas_select_v1",
    summary="Select liviano (Id, Nombre)",
)
def select_items(db: DbDep, q: str | None = Query(None)):
    q = q.strip() if isinstance(q, str) else q
    rows = svc.list_select(db, q)
    # rows = List[Tuple[Id, Nombre]]
    return [CatalogoSelectDTO(Id=r[0], Nombre=r[1] if len(r) > 1 else None) for r in rows]


@router.get(
    "/{id}",
    response_model=CatalogoDTO,
    operation_id="sistemas_get_v1",
    summary="Obtener sistema por Id",
)
def get_item(db: DbDep, id: Annotated[int, Path(..., ge=1)]):
    obj = svc.get(db, id)
    return CatalogoDTO.model_validate(obj)


@router.post(
    "",
    response_model=CatalogoDTO,
    status_code=status.HTTP_201_CREATED,
    operation_id="sistemas_create_v1",
    summary="(ADMIN) Crear sistema",
)
def create_item(
    payload: CatalogoCreate,
    db: DbDep,
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.create(db, payload, user=getattr(u, "Username", None))
    return CatalogoDTO.model_validate(obj)


@router.put(
    "/{id}",
    response_model=CatalogoDTO,
    operation_id="sistemas_update_v1",
    summary="(ADMIN) Actualizar sistema",
)
def update_item(
    id: Annotated[int, Path(..., ge=1)],
    payload: CatalogoUpdate,
    db: DbDep,
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.update(db, id, payload, user=getattr(u, "Username", None))
    return CatalogoDTO.model_validate(obj)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="sistemas_delete_v1",
    summary="(ADMIN) Eliminar sistema (soft-delete)",
)
def delete_item(
    id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, id, user=getattr(u, "Username", None))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
