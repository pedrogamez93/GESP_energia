from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.division_sistemas_detalle import (
    IluminacionDTO, IluminacionUpdate,
    CalefaccionDTO, CalefaccionUpdate,
    RefrigeracionDTO, RefrigeracionUpdate,
    ACSDTO, ACSUpdate,
    FotovoltaicoDTO, FotovoltaicoUpdate,
)
from app.services.division_sistemas_service import DivisionSistemasService

router = APIRouter(prefix="/api/v1/divisiones", tags=["Sistemas por División (detalle)"])
svc = DivisionSistemasService()

# ---------- Iluminación ----------
@router.get("/{division_id}/sistemas/iluminacion", response_model=IluminacionDTO)
def get_iluminacion(division_id: Annotated[int, Path(..., ge=1)], db: Session = Depends(get_db)):
    return IluminacionDTO(**svc.get_iluminacion(db, division_id))

@router.put("/{division_id}/sistemas/iluminacion", response_model=IluminacionDTO)
def put_iluminacion(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: IluminacionUpdate,
    db: Session = Depends(get_db),
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))] = None,
):
    out = svc.update_iluminacion(db, division_id, payload.model_dump(exclude_unset=True), getattr(u, "Username", None) if u else None)
    return IluminacionDTO(**out)

# ---------- Calefacción ----------
@router.get("/{division_id}/sistemas/calefaccion", response_model=CalefaccionDTO)
def get_calefaccion(division_id: Annotated[int, Path(..., ge=1)], db: Session = Depends(get_db)):
    return CalefaccionDTO(**svc.get_calefaccion(db, division_id))

@router.put("/{division_id}/sistemas/calefaccion", response_model=CalefaccionDTO)
def put_calefaccion(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: CalefaccionUpdate,
    db: Session = Depends(get_db),
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))] = None,
):
    out = svc.update_calefaccion(db, division_id, payload.model_dump(exclude_unset=True), getattr(u, "Username", None) if u else None)
    return CalefaccionDTO(**out)

# ---------- Refrigeración ----------
@router.get("/{division_id}/sistemas/refrigeracion", response_model=RefrigeracionDTO)
def get_refrigeracion(division_id: Annotated[int, Path(..., ge=1)], db: Session = Depends(get_db)):
    return RefrigeracionDTO(**svc.get_refrigeracion(db, division_id))

@router.put("/{division_id}/sistemas/refrigeracion", response_model=RefrigeracionDTO)
def put_refrigeracion(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: RefrigeracionUpdate,
    db: Session = Depends(get_db),
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))] = None,
):
    out = svc.update_refrigeracion(db, division_id, payload.model_dump(exclude_unset=True), getattr(u, "Username", None) if u else None)
    return RefrigeracionDTO(**out)

# ---------- ACS ----------
@router.get("/{division_id}/sistemas/acs", response_model=ACSDTO)
def get_acs(division_id: Annotated[int, Path(..., ge=1)], db: Session = Depends(get_db)):
    return ACSDTO(**svc.get_acs(db, division_id))

@router.put("/{division_id}/sistemas/acs", response_model=ACSDTO)
def put_acs(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: ACSUpdate,
    db: Session = Depends(get_db),
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))] = None,
):
    out = svc.update_acs(db, division_id, payload.model_dump(exclude_unset=True), getattr(u, "Username", None) if u else None)
    return ACSDTO(**out)

# ---------- Fotovoltaico ----------
@router.get("/{division_id}/sistemas/fotovoltaico", response_model=FotovoltaicoDTO)
def get_fv(division_id: Annotated[int, Path(..., ge=1)], db: Session = Depends(get_db)):
    return FotovoltaicoDTO(**svc.get_fotovoltaico(db, division_id))

@router.put("/{division_id}/sistemas/fotovoltaico", response_model=FotovoltaicoDTO)
def put_fv(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: FotovoltaicoUpdate,
    db: Session = Depends(get_db),
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))] = None,
):
    out = svc.update_fotovoltaico(db, division_id, payload.model_dump(exclude_unset=True), getattr(u, "Username", None) if u else None)
    return FotovoltaicoDTO(**out)
