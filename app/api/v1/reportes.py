from __future__ import annotations

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.services.reporte_service import ReporteService
from app.schemas.reporte import (
    SerieMensualDTO,
    ConsumoMedidorDTO,
    ConsumoNumeroClienteDTO,
    KPIsDTO,
)

router = APIRouter(prefix="/api/v1/reportes", tags=["Reportes"])
svc = ReporteService()
DbDep = Annotated[Session, Depends(get_db)]
Log = logging.getLogger(__name__)

# ✅ Roles que pueden LEER reportes
REPORTES_READ_ROLES = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_SERVICIO",
    "GESTOR_FLOTA",
    "GESTOR DE CONSULTA",
)

# Intentamos importar tabla puente para scope (si existe)
try:
    from app.db.models.usuarios_divisiones import UsuarioDivision  # type: ignore
except Exception:
    UsuarioDivision = None  # type: ignore


def _is_admin(u: UserPublic) -> bool:
    return "ADMINISTRADOR" in (u.roles or [])


def _ensure_actor_can_access_division(db: Session, actor: UserPublic, division_id: int) -> None:
    """
    ADMIN: puede ver cualquier DivisionId.
    No-admin: debe tener DivisionId dentro de su alcance (UsuarioDivision).
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
                "msg": "No tienes acceso a esta división.",
                "division_id": int(division_id),
            },
        )


def _require_division_for_non_admin(actor: UserPublic, division_id: Optional[int]) -> int:
    """
    Para reportes, si no es admin exigimos DivisionId para evitar reportes globales accidentales.
    """
    if _is_admin(actor):
        if division_id is None:
            raise HTTPException(
                status_code=400,
                detail={"code": "missing_division", "msg": "DivisionId es requerido."},
            )
        return int(division_id)

    if division_id is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "missing_division",
                "msg": "DivisionId es requerido para tu rol.",
            },
        )
    return int(division_id)


AuthUser = Annotated[UserPublic, Depends(require_roles(*REPORTES_READ_ROLES))]


@router.get(
    "/consumo-mensual",
    response_model=List[SerieMensualDTO],
    dependencies=[Depends(require_roles(*REPORTES_READ_ROLES))],
)
def consumo_mensual(
    db: DbDep,
    u: AuthUser,
    DivisionId: int = Query(..., ge=1),
    EnergeticoId: int = Query(..., ge=1),
    Desde: str = Query(..., description="YYYY-MM-01"),
    Hasta: str = Query(..., description="YYYY-MM-01 (exclusivo)"),
):
    # Aquí DivisionId viene obligatorio, pero igual validamos scope.
    _ensure_actor_can_access_division(db, u, int(DivisionId))

    rows = svc.serie_mensual(db, int(DivisionId), int(EnergeticoId), Desde, Hasta)
    return [SerieMensualDTO.model_validate(x) for x in rows]


@router.get(
    "/consumo-por-medidor",
    response_model=List[ConsumoMedidorDTO],
    dependencies=[Depends(require_roles(*REPORTES_READ_ROLES))],
)
def consumo_por_medidor(
    db: DbDep,
    u: AuthUser,
    DivisionId: int | None = Query(default=None, ge=1),
    EnergeticoId: int | None = Query(default=None, ge=1),
    Desde: str | None = Query(default=None, description="YYYY-MM-DD"),
    Hasta: str | None = Query(default=None, description="YYYY-MM-DD (exclusivo)"),
):
    # ✅ Exigimos DivisionId para evitar reportes globales por error (no-admin).
    div_id = _require_division_for_non_admin(u, DivisionId)
    _ensure_actor_can_access_division(db, u, div_id)

    rows = svc.consumo_por_medidor(
        db,
        div_id,
        int(EnergeticoId) if EnergeticoId is not None else None,
        Desde,
        Hasta,
    )
    return [ConsumoMedidorDTO.model_validate(x) for x in rows]


@router.get(
    "/consumo-por-numero-cliente",
    response_model=List[ConsumoNumeroClienteDTO],
    dependencies=[Depends(require_roles(*REPORTES_READ_ROLES))],
)
def consumo_por_num_cliente(
    db: DbDep,
    u: AuthUser,
    DivisionId: int | None = Query(default=None, ge=1),
    EnergeticoId: int | None = Query(default=None, ge=1),
    Desde: str | None = Query(default=None),
    Hasta: str | None = Query(default=None),
):
    div_id = _require_division_for_non_admin(u, DivisionId)
    _ensure_actor_can_access_division(db, u, div_id)

    rows = svc.consumo_por_num_cliente(
        db,
        div_id,
        int(EnergeticoId) if EnergeticoId is not None else None,
        Desde,
        Hasta,
    )
    return [ConsumoNumeroClienteDTO.model_validate(x) for x in rows]


@router.get(
    "/kpis",
    response_model=KPIsDTO,
    dependencies=[Depends(require_roles(*REPORTES_READ_ROLES))],
)
def kpis(
    db: DbDep,
    u: AuthUser,
    DivisionId: int | None = Query(default=None, ge=1),
    EnergeticoId: int | None = Query(default=None, ge=1),
    Desde: str | None = Query(default=None),
    Hasta: str | None = Query(default=None),
):
    div_id = _require_division_for_non_admin(u, DivisionId)
    _ensure_actor_can_access_division(db, u, div_id)

    data = svc.kpis(
        db,
        div_id,
        int(EnergeticoId) if EnergeticoId is not None else None,
        Desde,
        Hasta,
    )
    return KPIsDTO.model_validate(data)
