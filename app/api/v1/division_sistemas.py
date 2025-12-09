# app/api/v1/division_sistemas.py
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.division_sistemas import DivisionSistemasDTO, DivisionSistemasUpdate
from app.services.division_sistemas_service import DivisionSistemasService

router = APIRouter(prefix="/api/v1/divisiones", tags=["Sistemas por División"])
svc = DivisionSistemasService()


@router.get(
    "/{division_id}/sistemas",
    response_model=DivisionSistemasDTO,
    summary="Obtener configuración de sistemas para una División",
)
def get_division_sistemas(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
):
    div = svc.get(db, division_id)
    return svc.to_dto(div)


@router.put(
    "/{division_id}/sistemas",
    response_model=DivisionSistemasDTO,
    summary="Actualizar configuración de sistemas para una División",
)
def put_division_sistemas(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: DivisionSistemasUpdate,
    db: Session = Depends(get_db),
    u: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))] = None,
):
    updated = svc.update(
        db,
        division_id,
        payload=payload.model_dump(exclude_unset=True),
        user=getattr(u, "Username", None) if u else None,
    )
    return svc.to_dto(updated)


@router.get(
    "/{division_id}/sistemas/catalogos",
    summary="Catálogos para armar combos en la UI (luminarias, equipos, energéticos, colectores, compatibilidades)",
)
def get_division_sistemas_catalogs(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
):
    return svc.catalogs(db)
