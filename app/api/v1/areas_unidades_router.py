# app/api/v1/areas_unidades_router.py
from __future__ import annotations
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.unidades_areas_service import UnidadesAreasService

router = APIRouter(prefix="/api/v1/areas", tags=["Áreas ⇄ Unidades"])

# Auth dummy (ajústalo a tu proyecto)
class CurrentUser:
    def __init__(self, id: Optional[str], is_admin: bool):
        self.id = id
        self.is_admin = is_admin

def get_current_user() -> CurrentUser:
    return CurrentUser(id="system", is_admin=True)


@router.get("/{area_id}/unidad", response_model=Optional[int])
def get_unidad_de_area(
    area_id: int,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadesAreasService(db)
    return svc.get_unidad_by_area(area_id)


@router.post("/{area_id}/unidad/{unidad_id}", status_code=status.HTTP_200_OK)
def asignar_unidad_a_area(
    area_id: int,
    unidad_id: int,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadesAreasService(db)
    try:
        return svc.assign_exclusive(area_id, unidad_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{area_id}/unidad", status_code=status.HTTP_200_OK)
def desasignar_unidad_de_area(
    area_id: int,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadesAreasService(db)
    try:
        return svc.unassign(area_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
