from __future__ import annotations

import logging
from typing import Annotated, Tuple, Optional, TypeAlias

from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.numero_cliente import (
    NumeroClienteDTO,
    NumeroClienteCreate,
    NumeroClienteUpdate,
    NumeroClientePage,
    NumeroClienteDetalleDTO,
)
from app.services.numero_cliente_service import NumeroClienteService

router = APIRouter(prefix="/api/v1/numero-clientes", tags=["NúmeroClientes"])
svc = NumeroClienteService()
DbDep: TypeAlias = Annotated[Session, Depends(get_db)]
Log = logging.getLogger(__name__)

# ==========================================================
# ✅ ROLES
#   - LECTURA: incluye GESTOR DE CONSULTA
#   - ESCRITURA: todos los gestores operativos, NO gestor consulta
# ==========================================================
NUM_CLIENTE_READ_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_FLOTA",
    "GESTOR_SERVICIO",
    "GESTOR DE CONSULTA",
)

NUM_CLIENTE_WRITE_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_FLOTA",
    "GESTOR_SERVICIO",
)

ReadUserDep = Annotated[UserPublic, Depends(require_roles(*NUM_CLIENTE_READ_ROLES))]
WriteUserDep = Annotated[UserPublic, Depends(require_roles(*NUM_CLIENTE_WRITE_ROLES))]

# ==========================================================
# ✅ SCOPE por división (UsuarioDivision)
# ==========================================================
try:
    from app.db.models.usuarios_divisiones import UsuarioDivision  # type: ignore
except Exception:
    UsuarioDivision = None  # type: ignore

# Intento (opcional) de resolver DivisionId desde el modelo (si existe)
# Ajusta el import si tu archivo se llama distinto.
try:
    from app.db.models.numero_cliente import NumeroCliente  # type: ignore
except Exception:
    NumeroCliente = None  # type: ignore

# Si existe puente numero_cliente_division (no siempre existe), úsalo
try:
    from app.db.models.numero_cliente_division import NumeroClienteDivision  # type: ignore
except Exception:
    NumeroClienteDivision = None  # type: ignore


def _is_admin(u: UserPublic) -> bool:
    return "ADMINISTRADOR" in (u.roles or [])


def _ensure_scope_model_or_forbid(model, code: str, msg: str, extra: dict) -> None:
    if model is None:
        Log.warning("%s %s", code, extra)
        raise HTTPException(status_code=403, detail={"code": code, "msg": msg, **extra})


def _ensure_actor_can_access_division(db: Session, actor: UserPublic, division_id: int) -> None:
    """
    ADMIN: ok.
    No-admin: division_id debe estar en UsuarioDivision.
    """
    if _is_admin(actor):
        return

    _ensure_scope_model_or_forbid(
        UsuarioDivision,
        "forbidden_scope",
        "No se puede verificar alcance (UsuarioDivision no disponible).",
        {"division_id": int(division_id), "actor_id": getattr(actor, "id", None)},
    )

    ok = db.execute(
        select(UsuarioDivision.DivisionId)
        .where(
            UsuarioDivision.UsuarioId == actor.id,
            UsuarioDivision.DivisionId == int(division_id),
        )
        .limit(1)
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
    Para listados: no-admin debe filtrar por DivisionId para no exponer todo el universo.
    """
    if _is_admin(actor):
        # Admin puede listar sin DivisionId, pero por performance se recomienda enviarlo.
        if division_id is None:
            raise HTTPException(
                status_code=400,
                detail={"code": "missing_division", "msg": "DivisionId es requerido (por seguridad/performance)."},
            )
        return int(division_id)

    if division_id is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "missing_division", "msg": "DivisionId es requerido para tu rol."},
        )
    return int(division_id)


def _resolve_division_ids_for_numero_cliente(db: Session, num_cliente_id: int) -> list[int]:
    """
    Intenta resolver las DivisionId asociadas a un NúmeroCliente.
    A) puente NumeroClienteDivision (si existe)
    B) NumeroCliente.DivisionId (si existe)
    """
    # A) puente
    if NumeroClienteDivision is not None and hasattr(NumeroClienteDivision, "DivisionId"):
        rows = db.execute(
            select(NumeroClienteDivision.DivisionId).where(
                NumeroClienteDivision.NumeroClienteId == int(num_cliente_id)
            )
        ).all()
        divs = [int(r[0]) for r in rows if r and r[0] is not None]
        if divs:
            return divs

    # B) campo directo
    if NumeroCliente is not None and hasattr(NumeroCliente, "DivisionId"):
        row = db.execute(
            select(getattr(NumeroCliente, "DivisionId")).where(NumeroCliente.Id == int(num_cliente_id))
        ).first()
        div = int(row[0]) if row and row[0] is not None else None
        return [div] if div is not None else []

    return []


def _ensure_actor_can_access_numero_cliente(db: Session, actor: UserPublic, num_cliente_id: int) -> None:
    """
    ADMIN: ok.
    No-admin: debe estar asociado a al menos una división accesible.
    Si no se puede resolver asociación -> 403 (seguro).
    """
    if _is_admin(actor):
        return

    divs = _resolve_division_ids_for_numero_cliente(db, int(num_cliente_id))
    if not divs:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede validar alcance del número cliente (sin división asociada o modelo no disponible).",
                "num_cliente_id": int(num_cliente_id),
            },
        )

    for d in divs:
        try:
            _ensure_actor_can_access_division(db, actor, int(d))
            return
        except HTTPException:
            continue

    raise HTTPException(
        status_code=403,
        detail={
            "code": "forbidden_scope",
            "msg": "No tienes acceso a este número de cliente (fuera de tus divisiones).",
            "num_cliente_id": int(num_cliente_id),
        },
    )


# ==========================================================
# GET (LECTURA + scope)
# ==========================================================

@router.get(
    "",
    response_model=NumeroClientePage,
    summary="Listado paginado de número de clientes (global)",
)
def list_numero_clientes(
    db: DbDep,
    u: ReadUserDep,
    q: str | None = Query(default=None, description="Busca en Nº/NombreCliente"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    EmpresaDistribuidoraId: int | None = Query(default=None),
    TipoTarifaId: int | None = Query(default=None),
    active: bool | None = Query(default=True),
):
    """
    🔓 LISTADO GLOBAL
    - No exige DivisionId
    - No aplica scope
    - El uso/control queda en el frontend
    """
    return svc.list(
        db=db,
        q=q,
        page=page,
        page_size=page_size,
        EmpresaDistribuidoraId=EmpresaDistribuidoraId,
        TipoTarifaId=TipoTarifaId,
        DivisionId=None,  # explícito
        active=active,
    )


@router.get(
    "/{num_cliente_id}",
    response_model=NumeroClienteDTO,
    summary="Detalle (básico)",
)
def get_numero_cliente(
    num_cliente_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    u: ReadUserDep,
):
    _ensure_actor_can_access_numero_cliente(db, u, int(num_cliente_id))
    return svc.get(db, int(num_cliente_id))


@router.get(
    "/{num_cliente_id}/detalle",
    response_model=NumeroClienteDetalleDTO,
    summary="Detalle enriquecido (servicio, institución, región y dirección)",
)
def get_numero_cliente_detalle(
    num_cliente_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    u: ReadUserDep,
):
    _ensure_actor_can_access_numero_cliente(db, u, int(num_cliente_id))
    data = svc.detalle(db, int(num_cliente_id))
    return NumeroClienteDetalleDTO(**data)


# ==========================================================
# ESCRITURA (ADMIN + GESTORES operativos) con scope
# ==========================================================

@router.post(
    "",
    response_model=NumeroClienteDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMIN | GESTOR_*) Crear número de cliente",
)
def create_numero_cliente(
    payload: NumeroClienteCreate,
    db: DbDep,
    current_user: WriteUserDep,
):
    # ✅ Si el payload trae DivisionId, validamos alcance (si no lo trae, el service debería resolverlo)
    payload_div = getattr(payload, "DivisionId", None)
    if payload_div is not None:
        _ensure_actor_can_access_division(db, current_user, int(payload_div))

    return svc.create(db, payload, created_by=current_user.id)


@router.put(
    "/{num_cliente_id}",
    response_model=NumeroClienteDTO,
    summary="(ADMIN | GESTOR_*) Actualizar número de cliente",
)
def update_numero_cliente(
    num_cliente_id: Annotated[int, Path(..., ge=1)],
    payload: NumeroClienteUpdate,
    db: DbDep,
    current_user: WriteUserDep,
):
    # ✅ más robusto: validar alcance sobre el registro existente
    _ensure_actor_can_access_numero_cliente(db, current_user, int(num_cliente_id))
    return svc.update(db, int(num_cliente_id), payload, modified_by=current_user.id)


@router.delete(
    "/{num_cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMIN | GESTOR_*) Eliminar número de cliente (soft-delete)",
)
def delete_numero_cliente(
    num_cliente_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: WriteUserDep,
):
    _ensure_actor_can_access_numero_cliente(db, current_user, int(num_cliente_id))
    svc.soft_delete(db, int(num_cliente_id), modified_by=current_user.id)
    return None


@router.patch(
    "/{num_cliente_id}/reactivar",
    response_model=NumeroClienteDTO,
    summary="(ADMIN | GESTOR_*) Reactivar número de cliente",
)
def reactivate_numero_cliente(
    num_cliente_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: WriteUserDep,
):
    _ensure_actor_can_access_numero_cliente(db, current_user, int(num_cliente_id))
    return svc.reactivate(db, int(num_cliente_id), modified_by=current_user.id)
