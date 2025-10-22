# app/api/v1/areas.py
from __future__ import annotations
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Path, Query, status, Request, Response, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.db.models.area import Area

from app.schemas.pagination import Page, PageMeta
from app.schemas.areas import AreaDTO, AreaListDTO, AreaCreate, AreaUpdate
from app.schemas.links import LinkUnidades
from app.schemas.unidades import UnidadBrief

from app.services.area_service import AreaService
from app.services.area_units_service import (
    link_unidades_to_area,
    list_unidades_of_area,
    unlink_unidad_from_area,
)

router = APIRouter(prefix="/api/v1/areas", tags=["Áreas"])
DbDep = Annotated[Session, Depends(get_db)]


def _current_user_id(request: Request) -> str | None:
    return getattr(request.state, "user_id", None) or request.headers.get("X-User-Id")


# =========================
#        LIST & DETAIL
# =========================

@router.get("", response_model=Page[AreaListDTO], summary="Listado paginado/filtrado de áreas")
def list_areas(
    db: DbDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    PisoId: Optional[int] = Query(None, description="Filtra por Piso"),
    active: Optional[bool] = Query(True),
):
    svc = AreaService(db)
    total, items = svc.list_paged(page=page, page_size=page_size, piso_id=PisoId, active=active)
    pages = (total + page_size - 1) // page_size
    data = [AreaListDTO.model_validate(i) for i in items]
    return Page(data=data, meta=PageMeta(total=total, page=page, page_size=page_size, pages=pages))


@router.get("/{area_id}", response_model=AreaDTO, summary="Detalle de área")
def get_area(
    db: DbDep,
    area_id: int = Path(..., ge=1),
):
    svc = AreaService(db)
    obj = svc.get(area_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    return AreaDTO.model_validate(obj)


# =========================
#         CREATE/UPDATE
# =========================

@router.post("", response_model=AreaDTO, status_code=status.HTTP_201_CREATED, summary="Crear área")
def create_area(
    request: Request,
    db: DbDep,
    payload: AreaCreate,
):
    user_id = _current_user_id(request) or "system"
    svc = AreaService(db)
    obj = svc.create(payload, created_by=user_id)
    return AreaDTO.model_validate(obj)


@router.put("/{area_id}", response_model=AreaDTO, summary="Actualizar área (ADMIN)")
def update_area(
    request: Request,
    db: DbDep,
    payload: AreaUpdate,
    area_id: int = Path(..., ge=1),
):
    user_id = _current_user_id(request) or "system"
    svc = AreaService(db)
    obj = svc.update_admin(area_id, payload, modified_by=user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    return AreaDTO.model_validate(obj)


# =========================
#     SOFT-DELETE / UNDELETE
# =========================

@router.post("/delete/{area_id}", status_code=status.HTTP_204_NO_CONTENT,
             summary="Soft-delete de área (paridad .NET api/Areas/delete/{id})")
def soft_delete_area_compat(
    request: Request,
    db: DbDep,
    area_id: int = Path(..., ge=1),
):
    a = db.query(Area).filter(Area.Id == area_id).first()
    if not a:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    if not a.Active:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    now = datetime.utcnow()
    a.Active = False
    a.UpdatedAt = now
    a.ModifiedBy = _current_user_id(request)
    a.Version = (a.Version or 0) + 1
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{area_id}/reactivar", response_model=AreaDTO, summary="Reactivar área (Active=True)")
def reactivate_area(
    request: Request,
    db: DbDep,
    area_id: int = Path(..., ge=1),
):
    svc = AreaService(db)
    obj = svc.get(area_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    if not obj.Active:
        obj.Active = True
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = _current_user_id(request)
        obj.Version = (obj.Version or 0) + 1
        db.commit()
        db.refresh(obj)
    return AreaDTO.model_validate(obj)


# =========================
#     UNIDADES RELACIONADAS
# =========================

@router.post("/{area_id}/unidades", status_code=status.HTTP_200_OK, summary="Vincular Unidades a Área (bulk)")
def area_link_unidades(
    payload: LinkUnidades,
    area_id: int = Path(..., ge=1),
    db: DbDep = Depends(get_db),
):
    added = link_unidades_to_area(db, area_id, payload.unidades)
    return {"added": added}


@router.get("/{area_id}/unidades", response_model=list[UnidadBrief], summary="Listar Unidades del Área (detalle)")
def area_list_unidades(
    area_id: int = Path(..., ge=1),
    include_inactive: bool = Query(True),
    db: DbDep = Depends(get_db),
):
    rows = list_unidades_of_area(db, area_id, include_inactive=include_inactive)
    return [UnidadBrief(**r) for r in rows]


@router.delete("/{area_id}/unidades/{unidad_id}", status_code=status.HTTP_200_OK, summary="Desvincular Unidad de Área")
def area_unlink_unidad(
    area_id: int = Path(..., ge=1),
    unidad_id: int = Path(..., ge=1),
    db: DbDep = Depends(get_db),
):
    removed = unlink_unidad_from_area(db, area_id, unidad_id)
    return {"removed": removed}
