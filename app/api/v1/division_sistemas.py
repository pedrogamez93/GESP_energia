# app/api/v1/division_sistemas.py
from __future__ import annotations

import logging
from typing import Annotated, Tuple, TypeAlias

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.division_sistemas import DivisionSistemasDTO, DivisionSistemasUpdate
from app.services.division_sistemas_service import DivisionSistemasService

# Tabla puente para scope por división
try:
    from app.db.models.usuarios_divisiones import UsuarioDivision  # type: ignore
except Exception:  # pragma: no cover
    UsuarioDivision = None  # type: ignore

router = APIRouter(prefix="/api/v1/divisiones", tags=["Sistemas por División"])
svc = DivisionSistemasService()
Log = logging.getLogger(__name__)

DbDep: TypeAlias = Annotated[Session, Depends(get_db)]

# ==========================================================
# ✅ ROLES
#   - LECTURA: incluye GESTOR DE CONSULTA
#   - ESCRITURA: NO incluye GESTOR DE CONSULTA
# ==========================================================
DIVISION_SISTEMAS_READ_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_FLOTA",
    "GESTOR_SERVICIO",
    "GESTOR DE CONSULTA",
)

DIVISION_SISTEMAS_WRITE_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_FLOTA",
    "GESTOR_SERVICIO",
)

ReadUserDep = Annotated[UserPublic, Depends(require_roles(*DIVISION_SISTEMAS_READ_ROLES))]
WriteUserDep = Annotated[UserPublic, Depends(require_roles(*DIVISION_SISTEMAS_WRITE_ROLES))]


def _is_admin(u: UserPublic) -> bool:
    return "ADMINISTRADOR" in (u.roles or [])


def _ensure_actor_can_access_division(db: Session, actor: UserPublic, division_id: int) -> None:
    """
    ADMIN: ok
    No-admin: requiere vínculo en UsuarioDivision(UsuarioId, DivisionId)

    Si UsuarioDivision no existe/importa, NO abrimos (403).
    """
    if _is_admin(actor):
        return

    if UsuarioDivision is None:
        Log.warning(
            "forbidden_scope(no UsuarioDivision) actor=%s roles=%s division_id=%s",
            getattr(actor, "id", None),
            getattr(actor, "roles", None),
            int(division_id),
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar el alcance del gestor (modelo UsuarioDivision no disponible).",
                "division_id": int(division_id),
            },
        )

    exists = db.execute(
        select(UsuarioDivision.DivisionId)
        .where(
            UsuarioDivision.UsuarioId == actor.id,
            UsuarioDivision.DivisionId == int(division_id),
        )
        .limit(1)
    ).first()

    if not exists:
        Log.warning(
            "forbidden_scope actor=%s roles=%s division_id=%s",
            getattr(actor, "id", None),
            getattr(actor, "roles", None),
            int(division_id),
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No tienes acceso a esta división.",
                "division_id": int(division_id),
            },
        )


def ensure_actor_can_edit_division(db: Session, actor: UserPublic, division_id: int) -> None:
    """
    Escritura = mismo scope que lectura (pero sólo para roles write).
    """
    _ensure_actor_can_access_division(db, actor, int(division_id))


# ==========================================================
# GET (lectura + scope)
# ==========================================================
@router.get(
    "/{division_id}/sistemas",
    response_model=DivisionSistemasDTO,
    summary="Obtener configuración de sistemas para una División",
)
def get_division_sistemas(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    u: ReadUserDep,
):
    _ensure_actor_can_access_division(db, u, int(division_id))
    div = svc.get(db, int(division_id))
    return svc.to_dto(div)


@router.get(
    "/{division_id}/sistemas/catalogos",
    summary="Catálogos para armar combos en la UI (luminarias, equipos, energéticos, colectores, compatibilidades)",
)
def get_division_sistemas_catalogs(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    u: ReadUserDep,
):
    _ensure_actor_can_access_division(db, u, int(division_id))
    return svc.catalogs(db)


# ==========================================================
# PUT (escritura + scope) — NO incluye gestor consulta
# ==========================================================
@router.put(
    "/{division_id}/sistemas",
    response_model=DivisionSistemasDTO,
    summary="Actualizar configuración de sistemas para una División",
)
def put_division_sistemas(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: DivisionSistemasUpdate,
    db: DbDep,
    u: WriteUserDep,
):
    ensure_actor_can_edit_division(db, u, int(division_id))

    updated = svc.update(
        db,
        int(division_id),
        payload=payload.model_dump(exclude_unset=True),
        user=getattr(u, "Username", None),
    )

    Log.info(
        "PUT division_sistemas ok division_id=%s actor_id=%s roles=%s",
        int(division_id),
        getattr(u, "id", None),
        getattr(u, "roles", None),
    )

    return svc.to_dto(updated)
