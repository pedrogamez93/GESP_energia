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

# Roles que pueden ESCRIBIR configuración de sistemas
DIVISION_SISTEMAS_WRITE_ROLES = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_FLOTA",
    "GESTOR_SERVICIO",
)

# Intentamos importar la tabla puente para scope (si existe en tu proyecto)
# Si no existe, NO abrimos escritura a gestores sin validación.
try:
    from app.db.models.usuarios_divisiones import UsuarioDivision  # type: ignore
except Exception:
    UsuarioDivision = None  # type: ignore


def _ensure_actor_can_edit_division(db: Session, actor: UserPublic, division_id: int) -> None:
    """
    ADMIN: puede editar cualquier división.
    Gestores: solo pueden editar divisiones dentro de su alcance (tabla puente UsuarioDivision).

    Si no tienes ese modelo/tabla, deja 403 para gestores (por seguridad).
    """
    roles = actor.roles or []

    if "ADMINISTRADOR" in roles:
        return

    if UsuarioDivision is None:
        Log.warning(
            "forbidden_scope (no UsuarioDivision) actor=%s roles=%s division_id=%s",
            getattr(actor, "id", None),
            roles,
            division_id,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar alcance del gestor (UsuarioDivision no disponible).",
                "division_id": division_id,
            },
        )

    ok = db.execute(
        select(UsuarioDivision.DivisionId).where(
            UsuarioDivision.UsuarioId == actor.id,
            UsuarioDivision.DivisionId == division_id,
        )
    ).first()

    if not ok:
        Log.warning(
            "forbidden_scope actor=%s roles=%s division_id=%s",
            getattr(actor, "id", None),
            roles,
            division_id,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No puedes modificar esta división (fuera de tu alcance).",
                "division_id": division_id,
            },
        )


# ---------- Iluminación ----------
@router.get("/{division_id}/sistemas/iluminacion", response_model=IluminacionDTO)
def get_iluminacion(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
):
    return IluminacionDTO(**svc.get_iluminacion(db, division_id))


@router.put("/{division_id}/sistemas/iluminacion", response_model=IluminacionDTO)
def put_iluminacion(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: IluminacionUpdate,
    db: Session = Depends(get_db),
    u: Annotated[UserPublic, Depends(require_roles(*DIVISION_SISTEMAS_WRITE_ROLES))] = None,
):
    if u:
        _ensure_actor_can_edit_division(db, u, division_id)

    out = svc.update_iluminacion(
        db,
        division_id,
        payload.model_dump(exclude_unset=True),
        getattr(u, "Username", None) if u else None,
    )
    return IluminacionDTO(**out)


# ---------- Calefacción ----------
@router.get("/{division_id}/sistemas/calefaccion", response_model=CalefaccionDTO)
def get_calefaccion(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
):
    return CalefaccionDTO(**svc.get_calefaccion(db, division_id))


@router.put("/{division_id}/sistemas/calefaccion", response_model=CalefaccionDTO)
def put_calefaccion(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: CalefaccionUpdate,
    db: Session = Depends(get_db),
    u: Annotated[UserPublic, Depends(require_roles(*DIVISION_SISTEMAS_WRITE_ROLES))] = None,
):
    if u:
        _ensure_actor_can_edit_division(db, u, division_id)

    out = svc.update_calefaccion(
        db,
        division_id,
        payload.model_dump(exclude_unset=True),
        getattr(u, "Username", None) if u else None,
    )
    return CalefaccionDTO(**out)


# ---------- Refrigeración ----------
@router.get("/{division_id}/sistemas/refrigeracion", response_model=RefrigeracionDTO)
def get_refrigeracion(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
):
    return RefrigeracionDTO(**svc.get_refrigeracion(db, division_id))


@router.put("/{division_id}/sistemas/refrigeracion", response_model=RefrigeracionDTO)
def put_refrigeracion(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: RefrigeracionUpdate,
    db: Session = Depends(get_db),
    u: Annotated[UserPublic, Depends(require_roles(*DIVISION_SISTEMAS_WRITE_ROLES))] = None,
):
    if u:
        _ensure_actor_can_edit_division(db, u, division_id)

    out = svc.update_refrigeracion(
        db,
        division_id,
        payload.model_dump(exclude_unset=True),
        getattr(u, "Username", None) if u else None,
    )
    return RefrigeracionDTO(**out)


# ---------- ACS ----------
@router.get("/{division_id}/sistemas/acs", response_model=ACSDTO)
def get_acs(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
):
    return ACSDTO(**svc.get_acs(db, division_id))


@router.put("/{division_id}/sistemas/acs", response_model=ACSDTO)
def put_acs(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: ACSUpdate,
    db: Session = Depends(get_db),
    u: Annotated[UserPublic, Depends(require_roles(*DIVISION_SISTEMAS_WRITE_ROLES))] = None,
):
    if u:
        _ensure_actor_can_edit_division(db, u, division_id)

    out = svc.update_acs(
        db,
        division_id,
        payload.model_dump(exclude_unset=True),
        getattr(u, "Username", None) if u else None,
    )
    return ACSDTO(**out)


# ---------- Fotovoltaico ----------
@router.get("/{division_id}/sistemas/fotovoltaico", response_model=FotovoltaicoDTO)
def get_fv(
    division_id: Annotated[int, Path(..., ge=1)],
    db: Session = Depends(get_db),
):
    return FotovoltaicoDTO(**svc.get_fotovoltaico(db, division_id))


@router.put("/{division_id}/sistemas/fotovoltaico", response_model=FotovoltaicoDTO)
def put_fv(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: FotovoltaicoUpdate,
    db: Session = Depends(get_db),
    u: Annotated[UserPublic, Depends(require_roles(*DIVISION_SISTEMAS_WRITE_ROLES))] = None,
):
    if u:
        _ensure_actor_can_edit_division(db, u, division_id)

    out = svc.update_fotovoltaico(
        db,
        division_id,
        payload.model_dump(exclude_unset=True),
        getattr(u, "Username", None) if u else None,
    )
    return FotovoltaicoDTO(**out)
