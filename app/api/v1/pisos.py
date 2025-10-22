from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status, Request, Response, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.db.models.piso import Piso
from app.db.models.area import Area

from app.schemas.pagination import Page, PageMeta
from app.schemas.pisos import PisoDTO, PisoListDTO, PisoCreate, PisoUpdate
from app.schemas.links import LinkUnidades
from app.schemas.unidades import UnidadBrief

from app.services.piso_service import PisoService
from app.services.piso_units_service import (
    link_unidades_to_piso,
    list_unidades_of_piso,
    unlink_unidad_from_piso,
)

router = APIRouter(prefix="/api/v1/pisos", tags=["Pisos"])


def _current_user_id(request: Request) -> str | None:
    return getattr(request.state, "user_id", None) or request.headers.get("X-User-Id")


# =========================
#        LIST & DETAIL
# =========================

@router.get("", response_model=Page[PisoListDTO], summary="Listado paginado/filtrado de pisos")
def list_pisos(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    DivisionId: Optional[int] = Query(None, description="Filtra por División (edificio)"),
    active: Optional[bool] = Query(True),
):
    svc = PisoService(db)
    total, items = svc.list_paged(page=page, page_size=page_size, division_id=DivisionId, active=active)
    pages = (total + page_size - 1) // page_size
    data = [PisoListDTO.model_validate(i) for i in items]
    return Page(data=data, meta=PageMeta(total=total, page=page, page_size=page_size, pages=pages))


@router.get("/{piso_id}", response_model=PisoDTO, summary="Detalle de piso")
def get_piso(
    db: Session = Depends(get_db),
    piso_id: int = Path(..., ge=1),
):
    svc = PisoService(db)
    obj = svc.get(piso_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Piso no encontrado")
    return PisoDTO.model_validate(obj)


# =========================
#         CREATE/UPDATE
# =========================

@router.post("", response_model=PisoDTO, status_code=status.HTTP_201_CREATED, summary="Crear piso")
def create_piso(
    request: Request,
    payload: PisoCreate,   # <-- primero
    db: DbDep = Depends(get_db),
):
    user_id = _current_user_id(request) or "system"
    svc = PisoService(db)
    obj = svc.create(payload, created_by=user_id)
    return PisoDTO.model_validate(obj)


@router.put("/{piso_id}", response_model=PisoDTO, summary="Actualizar piso (ADMIN)")
def update_piso(
    request: Request,
    payload: PisoUpdate,   # <-- primero
    piso_id: int = Path(..., ge=1),
    db: DbDep = Depends(get_db),
):
    user_id = _current_user_id(request) or "system"
    svc = PisoService(db)
    obj = svc.update_admin(piso_id, payload, modified_by=user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Piso no encontrado")
    return PisoDTO.model_validate(obj)


# =========================
#     SOFT-DELETE / UNDELETE
# =========================

@router.post("/delete/{piso_id}", status_code=status.HTTP_204_NO_CONTENT,
             summary="Soft-delete de piso (paridad .NET api/Pisos/delete/{id})")
def soft_delete_piso_compat(
    request: Request,
    db: Session = Depends(get_db),
    piso_id: int = Path(..., ge=1),
):
    p = db.query(Piso).filter(Piso.Id == piso_id).first()
    if not p:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    now = datetime.utcnow()
    user_id = _current_user_id(request)

    if p.Active:
        p.Active = False
        p.UpdatedAt = now
        p.ModifiedBy = user_id
        p.Version = (p.Version or 0) + 1

    # Soft-delete en cascada de Áreas del piso
    areas = db.query(Area).filter(Area.PisoId == piso_id, Area.Active == True).all()
    for a in areas:
        a.Active = False
        a.UpdatedAt = now
        a.ModifiedBy = user_id
        a.Version = (a.Version or 0) + 1

    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{piso_id}/reactivar", response_model=PisoDTO, summary="Reactivar piso (Active=True)")
def reactivate_piso(
    request: Request,
    db: Session = Depends(get_db),
    piso_id: int = Path(..., ge=1),
):
    svc = PisoService(db)
    obj = svc.get(piso_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Piso no encontrado")
    if not obj.Active:
        obj.Active = True
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = _current_user_id(request)
        obj.Version = (obj.Version or 0) + 1
        db.commit()
        db.refresh(obj)
    return PisoDTO.model_validate(obj)


# =========================
#     UNIDADES RELACIONADAS
# =========================

@router.post("/{piso_id}/unidades", status_code=status.HTTP_200_OK, summary="Vincular Unidades a Piso (bulk)")
def piso_link_unidades(
    payload: LinkUnidades,
    piso_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    added = link_unidades_to_piso(db, piso_id, payload.unidades)
    return {"added": added}


@router.get("/{piso_id}/unidades", response_model=list[UnidadBrief], summary="Listar Unidades del Piso (detalle)")
def piso_list_unidades(
    piso_id: int = Path(..., ge=1),
    include_inactive: bool = Query(True),
    db: Session = Depends(get_db),
):
    rows = list_unidades_of_piso(db, piso_id, include_inactive=include_inactive)
    return [UnidadBrief(**r) for r in rows]


@router.delete("/{piso_id}/unidades/{unidad_id}", status_code=status.HTTP_200_OK, summary="Desvincular Unidad de Piso")
def piso_unlink_unidad(
    piso_id: int = Path(..., ge=1),
    unidad_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    removed = unlink_unidad_from_piso(db, piso_id, unidad_id)
    return {"removed": removed}
