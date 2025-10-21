# app/api/v1/unidad_router.py
from __future__ import annotations
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, Path, status, Response, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.unidad import (
    UnidadDTO, UnidadListDTO, UnidadFilterDTO, Page
)
from app.services.unidad_service import UnidadService

router = APIRouter(prefix="/api/v1/unidades", tags=["Unidades"])
DbDep = Annotated[Session, Depends(get_db)]


# ---------- LECTURAS / LISTADOS ----------
@router.get(
    "/filter",
    response_model=Page[UnidadListDTO],
    summary="Listado paginado por filtro"
)
def list_unidades_filter(
    db: DbDep,
    unidad: Optional[str] = Query(None),
    userId: Optional[str] = Query(None),
    institucionId: Optional[int] = Query(None),
    servicioId: Optional[int] = Query(None),
    regionId: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    svc = UnidadService(db)
    f = UnidadFilterDTO(
        Unidad=unidad, userId=userId, InstitucionId=institucionId,
        ServicioId=servicioId, RegionId=regionId
    )
    return svc.list_filter(f, page, page_size)


@router.get(
    "/getasociadosbyuser/{user_id}",
    response_model=List[UnidadListDTO],
    summary="Unidades asociadas a un usuario"
)
def list_asociados_by_user(user_id: str, db: DbDep):
    svc = UnidadService(db)
    return svc.list_asociados_by_user(user_id)


@router.get(
    "/getbyfilter",
    response_model=List[UnidadListDTO],
    summary="Listado NO paginado por filtro (uso puntual)"
)
def get_by_filter(
    db: DbDep,
    userId: Optional[str] = Query(None),
    institucionId: Optional[int] = Query(None),
    servicioId: Optional[int] = Query(None),
    regionId: Optional[int] = Query(None),
):
    svc = UnidadService(db)
    f = UnidadFilterDTO(
        Unidad=None, userId=userId, InstitucionId=institucionId,
        ServicioId=servicioId, RegionId=regionId
    )
    page = svc.list_filter(f, page=1, page_size=100_000)
    return page.data


@router.get(
    "/hasInteligentMeasurement/{old_id}",
    response_model=bool,
    summary="¿Tiene medición inteligente?"
)
def has_inteligent_measurement(old_id: int, db: DbDep):
    svc = UnidadService(db)
    return svc.has_inteligent_measurement(old_id)


@router.get(
    "/{nombre}/{servicio_id}",
    response_model=bool,
    summary="Valida existencia de nombre por Servicio"
)
def check_unidad_nombre(nombre: str, servicio_id: int, db: DbDep):
    svc = UnidadService(db)
    return svc.check_nombre(nombre, servicio_id)


@router.get(
    "/{unidad_id}",
    response_model=UnidadDTO,
    summary="Detalle de unidad"
)
def get_unidad(unidad_id: Annotated[int, Path(ge=1)], db: DbDep):
    svc = UnidadService(db)
    try:
        return svc.get(unidad_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


# ---------- ADMIN (crear/actualizar/eliminar) ----------
@router.post(
    "",
    response_model=UnidadDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMINISTRADOR) Crear unidad"
)
def create_unidad(
    payload: dict,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc = UnidadService(db)
    try:
        return svc.create(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/{unidad_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMINISTRADOR) Actualizar unidad"
)
def update_unidad(
    unidad_id: Annotated[int, Path(ge=1)],
    payload: dict,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc = UnidadService(db)
    try:
        svc.update(unidad_id, payload)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{unidad_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMINISTRADOR) Eliminar unidad"
)
def delete_unidad(
    unidad_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc = UnidadService(db)
    svc.delete(unidad_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
