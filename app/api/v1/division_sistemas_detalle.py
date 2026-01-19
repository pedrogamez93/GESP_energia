from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
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
Log = logging.getLogger(__name__)

# ✅ Roles que pueden LEER
DIVISION_SISTEMAS_READ_ROLES = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_FLOTA",
    "GESTOR_SERVICIO",
    "GESTOR DE CONSULTA",
)

# ✅ Roles que pueden ESCRIBIR
DIVISION_SISTEMAS_WRITE_ROLES = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_FLOTA",
    "GESTOR_SERVICIO",
)

try:
    from app.db.models.usuarios_divisiones import UsuarioDivision  # type: ignore
except Exception:
    UsuarioDivision = None  # type: ignore


def _is_admin(actor: UserPublic) -> bool:
    return "ADMINISTRADOR" in (actor.roles or [])


def _ensure_actor_can_access_division(db: Session, actor: UserPublic, division_id: int) -> None:
    """
    ADMIN: ok.
    No-admin: debe tener la DivisionId en su alcance (UsuarioDivision).
    """
    if _is_admin(actor):
        return

    if UsuarioDivision is None:
        Log.warning(
            "forbidden_scope (no UsuarioDivision) actor=%s roles=%s division_id=%s",
            getattr(actor, "id", None),
            actor.roles,
            division_id,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar alcance (UsuarioDivision no disponible).",
                "division_id": int(division_id),
            },
        )

    ok = db.execute(
        select(UsuarioDivision.DivisionId).where(
            UsuarioDivision.UsuarioId == actor.id,
            UsuarioDivision.DivisionId == int(division_id),
        )
    ).first()

    if not ok:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "Fuera de tu alcance (división).",
                "division_id": int(division_id),
            },
        )


# Dependencias reutilizables
ReadUser = Annotated[UserPublic, Depends(require_roles(*DIVISION_SISTEMAS_READ_ROLES))]
WriteUser = Annotated[UserPublic, Depends(require_roles(*DIVISION_SISTEMAS_WRITE_ROLES))]


# ---------- Iluminación ----------
@router.get(
    "/{division_id}/sistemas/iluminacion",
    response_model=IluminacionDTO,
    dependencies=[Depends(require_roles(*DIVISION_SISTEMAS_READ_ROLES))],
)
def get_iluminacion(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
    u: ReadUser = None,
):
    # u nunca debiera ser None por dependencies, pero lo dejamos simple
    _ensure_actor_can_access_division(db, u, division_id)
    return IluminacionDTO(**svc.get_iluminacion(db, division_id))


@router.put(
    "/{division_id}/sistemas/iluminacion",
    response_model=IluminacionDTO,
)
def put_iluminacion(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: IluminacionUpdate,
    db: Session = Depends(get_db),
    u: WriteUser = None,
):
    _ensure_actor_can_access_division(db, u, division_id)
    out = svc.update_iluminacion(
        db,
        division_id,
        payload.model_dump(exclude_unset=True),
        getattr(u, "Username", None),
    )
    return IluminacionDTO(**out)


# ---------- Calefacción ----------
@router.get(
    "/{division_id}/sistemas/calefaccion",
    response_model=CalefaccionDTO,
    dependencies=[Depends(require_roles(*DIVISION_SISTEMAS_READ_ROLES))],
)
def get_calefaccion(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
    u: ReadUser = None,
):
    _ensure_actor_can_access_division(db, u, division_id)
    return CalefaccionDTO(**svc.get_calefaccion(db, division_id))


@router.put(
    "/{division_id}/sistemas/calefaccion",
    response_model=CalefaccionDTO,
)
def put_calefaccion(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: CalefaccionUpdate,
    db: Session = Depends(get_db),
    u: WriteUser = None,
):
    _ensure_actor_can_access_division(db, u, division_id)
    out = svc.update_calefaccion(
        db,
        division_id,
        payload.model_dump(exclude_unset=True),
        getattr(u, "Username", None),
    )
    return CalefaccionDTO(**out)


# ---------- Refrigeración ----------
@router.get(
    "/{division_id}/sistemas/refrigeracion",
    response_model=RefrigeracionDTO,
    dependencies=[Depends(require_roles(*DIVISION_SISTEMAS_READ_ROLES))],
)
def get_refrigeracion(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
    u: ReadUser = None,
):
    _ensure_actor_can_access_division(db, u, division_id)
    return RefrigeracionDTO(**svc.get_refrigeracion(db, division_id))


@router.put(
    "/{division_id}/sistemas/refrigeracion",
    response_model=RefrigeracionDTO,
)
def put_refrigeracion(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: RefrigeracionUpdate,
    db: Session = Depends(get_db),
    u: WriteUser = None,
):
    _ensure_actor_can_access_division(db, u, division_id)
    out = svc.update_refrigeracion(
        db,
        division_id,
        payload.model_dump(exclude_unset=True),
        getattr(u, "Username", None),
    )
    return RefrigeracionDTO(**out)


# ---------- ACS ----------
@router.get(
    "/{division_id}/sistemas/acs",
    response_model=ACSDTO,
    dependencies=[Depends(require_roles(*DIVISION_SISTEMAS_READ_ROLES))],
)
def get_acs(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
    u: ReadUser = None,
):
    _ensure_actor_can_access_division(db, u, division_id)
    return ACSDTO(**svc.get_acs(db, division_id))


@router.put(
    "/{division_id}/sistemas/acs",
    response_model=ACSDTO,
)
def put_acs(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: ACSUpdate,
    db: Session = Depends(get_db),
    u: WriteUser = None,
):
    _ensure_actor_can_access_division(db, u, division_id)
    out = svc.update_acs(
        db,
        division_id,
        payload.model_dump(exclude_unset=True),
        getattr(u, "Username", None),
    )
    return ACSDTO(**out)


# ---------- Fotovoltaico ----------
@router.get(
    "/{division_id}/sistemas/fotovoltaico",
    response_model=FotovoltaicoDTO,
    dependencies=[Depends(require_roles(*DIVISION_SISTEMAS_READ_ROLES))],
)
def get_fv(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
    u: ReadUser = None,
):
    _ensure_actor_can_access_division(db, u, division_id)
    return FotovoltaicoDTO(**svc.get_fotovoltaico(db, division_id))


@router.put(
    "/{division_id}/sistemas/fotovoltaico",
    response_model=FotovoltaicoDTO,
)
def put_fv(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: FotovoltaicoUpdate,
    db: Session = Depends(get_db),
    u: WriteUser = None,
):
    _ensure_actor_can_access_division(db, u, division_id)
    out = svc.update_fotovoltaico(
        db,
        division_id,
        payload.model_dump(exclude_unset=True),
        getattr(u, "Username", None),
    )
    return FotovoltaicoDTO(**out)
