from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.pagination import Page
from app.schemas.unidad import (
    UnidadDTO,
    UnidadListDTO,
    UnidadFilterDTO,
    UnidadPatchDTO,
    LinkInmueblesRequest,
    LinkResult,
    UnidadWithInmueblesDTO,
)
from app.services.unidad_service import UnidadService

router = APIRouter(prefix="/api/v1/unidades", tags=["Unidades"])


# --------- Auth dummy (ajusta a tu proyecto) ----------
class CurrentUser:
    def __init__(self, id: Optional[str], is_admin: bool):
        self.id = id
        self.is_admin = is_admin


def get_current_user() -> CurrentUser:
    return CurrentUser(id="system", is_admin=True)


# ================== RUTAS ESTÁTICAS / ESPECÍFICAS PRIMERO ==================

@router.get("/filter", response_model=Page[UnidadListDTO])
def list_unidades_filter(
    unidad: Optional[str] = Query(None),
    userId: Optional[str] = Query(None),
    institucionId: Optional[int] = Query(None),
    servicioId: Optional[int] = Query(None),
    regionId: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    f = UnidadFilterDTO(
        Unidad=unidad,
        userId=userId,
        InstitucionId=institucionId,
        ServicioId=servicioId,
        RegionId=regionId,
    )
    return svc.list_filter(f, page, page_size)


@router.get("/getasociadosbyuser/{user_id}", response_model=List[UnidadListDTO])
def list_asociados_by_user(
    user_id: str,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    return svc.list_asociados_by_user(user_id)


@router.get("/getbyfilter", response_model=List[UnidadListDTO])
def get_by_filter(
    userId: Optional[str] = Query(None),
    institucionId: Optional[int] = Query(None),
    servicioId: Optional[int] = Query(None),
    regionId: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    f = UnidadFilterDTO(
        Unidad=None,
        userId=userId,
        InstitucionId=institucionId,
        ServicioId=servicioId,
        RegionId=regionId,
    )
    page = svc.list_filter(f, page=1, page_size=100000)
    return [UnidadListDTO.model_validate(x) for x in page.data]


# ────────────────────────────────────────────────
# NUEVO: Unidades por Servicio (id en la ruta)
# ────────────────────────────────────────────────
@router.get("/por-servicio/{servicio_id}", response_model=List[UnidadListDTO])
def list_unidades_by_servicio(
    servicio_id: int,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    """
    Retorna todas las unidades asociadas a un ServicioId dado.
    No hay paginación, se devuelven todas las coincidencias.
    """
    svc = UnidadService(db, me.id, me.is_admin)
    f = UnidadFilterDTO(
        Unidad=None,
        userId=None,
        InstitucionId=None,
        ServicioId=servicio_id,
        RegionId=None,
    )
    page = svc.list_filter(f, page=1, page_size=100000)
    return [UnidadListDTO.model_validate(x) for x in page.data]


@router.get("/check/{nombre}/{servicio_id}", response_model=bool)
def check_unidad_nombre(
    nombre: str,
    servicio_id: int,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    return svc.check_nombre(nombre, servicio_id)


@router.get("/hasInteligentMeasurement/{old_id}", response_model=bool)
def has_inteligent_measurement(
    old_id: int,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    return svc.has_inteligent_measurement(old_id)


@router.post("", response_model=UnidadDTO, status_code=status.HTTP_201_CREATED)
def create_unidad(
    payload: dict,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    try:
        return svc.create(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{unidad_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_unidad(
    unidad_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    try:
        svc.update(unidad_id, payload)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    return None


@router.delete("/{unidad_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unidad(
    unidad_id: int,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    svc.delete(unidad_id)
    return None


@router.get("/{unidad_id}", response_model=UnidadDTO)
def get_unidad(
    unidad_id: int,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    try:
        return svc.get(unidad_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


# ==================================================================
#                     NUEVAS RUTAS (no rompen nada)
# ==================================================================

@router.get("/{unidad_id}/inmuebles", response_model=List[int])
def list_inmuebles_ids(
    unidad_id: int,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    return svc.list_inmuebles_ids(unidad_id)


@router.post("/{unidad_id}/inmuebles", response_model=LinkResult)
def add_inmuebles_bulk(
    unidad_id: int,
    body: LinkInmueblesRequest,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    try:
        return svc.link_inmuebles_append(unidad_id, body.inmuebles)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.put("/{unidad_id}/inmuebles", response_model=LinkResult)
def sync_inmuebles_bulk(
    unidad_id: int,
    body: LinkInmueblesRequest,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    try:
        return svc.link_inmuebles_sync(unidad_id, body.inmuebles)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/{unidad_id}/expand", response_model=UnidadWithInmueblesDTO)
def get_unidad_expand(
    unidad_id: int,
    db: Session = Depends(get_db),
    me: CurrentUser = Depends(get_current_user),
):
    svc = UnidadService(db, me.id, me.is_admin)
    try:
        return svc.get_with_expand(unidad_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
