from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.catalogo_simple import CatalogoDTO, CatalogoSelectDTO, CatalogoCreate, CatalogoUpdate
from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.services.catalogo_simple_service import CatalogoSimpleService

router = APIRouter(prefix="/api/v1/tipos-equipos-calefaccion", tags=["Equipos calefacción"])
svc = CatalogoSimpleService(TipoEquipoCalefaccion, has_audit=True)
DbDep = Annotated[Session, Depends(get_db)]

@router.get("", response_model=dict)
def list_items(db: DbDep, q: str | None = Query(None), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    return svc.list(db, q, page, page_size)

@router.get("/select", response_model=List[CatalogoSelectDTO])
def select_items(db: DbDep, q: str | None = Query(None)):
    rows = svc.list_select(db, q)
    return [CatalogoSelectDTO(Id=r[0], Nombre=r[1] if len(r) > 1 else None) for r in rows]

@router.get("/{id}", response_model=CatalogoDTO)
def get_item(db: DbDep, id: Annotated[int, Path(..., ge=1)]):
    return svc.get(db, id)

@router.post("", response_model=CatalogoDTO, status_code=status.HTTP_201_CREATED, summary="(ADMIN) Crear tipo de equipo de calefacción")
def create_item(payload: CatalogoCreate, db: DbDep, _u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    return svc.create(db, payload)

@router.put("/{id}", response_model=CatalogoDTO, summary="(ADMIN) Actualizar tipo de equipo de calefacción")
def update_item(id: int, payload: CatalogoUpdate, db: DbDep, _u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    return svc.update(db, id, payload)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="(ADMIN) Eliminar tipo de equipo de calefacción (soft-delete)")
def delete_item(id: int, db: DbDep, _u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))]):
    svc.delete(db, id); return None
