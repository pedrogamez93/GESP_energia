# app/services/inmueble_scope.py
from __future__ import annotations

from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.schemas.auth import UserPublic
from app.db.models.division import Division

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def is_admin(user: UserPublic) -> bool:
    return "ADMINISTRADOR" in (user.roles or [])


def _get_actor_servicio_ids(db: Session, actor_id: str) -> List[int]:
    """
    Obtiene los ServicioId asociados al usuario desde la tabla REAL:
    dbo.UsuariosServicios (UsuarioId GUID/string, ServicioId int)
    """
    sql = text("""
        SELECT DISTINCT us.ServicioId
        FROM dbo.UsuariosServicios us WITH (NOLOCK)
        WHERE us.UsuarioId = :uid
    """)
    rows = db.execute(sql, {"uid": str(actor_id)}).fetchall()
    out: List[int] = []
    for r in rows:
        try:
            out.append(int(r[0]))
        except Exception:
            continue
    return out


def _get_division_servicio_id(db: Session, division_id: int) -> Optional[int]:
    row = db.execute(
        select(Division.ServicioId)
        .where(Division.Id == int(division_id))
        .limit(1)
    ).first()
    if not row:
        return None
    return int(row[0]) if row[0] is not None else None


# ─────────────────────────────────────────────
# Scope: División / Inmueble
# ─────────────────────────────────────────────

def ensure_actor_can_edit_division(
    db: Session,
    actor: UserPublic,
    division_id: int,
) -> None:
    """
    Scope para operar sobre un inmueble/división.

    Reglas:
    ✅ ADMIN: todo
    ✅ No-admin: permitido SOLO si el ServicioId del inmueble
       está dentro de los servicios del actor (dbo.UsuariosServicios)

    Fail-closed: si no se puede validar, se bloquea.
    """

    if is_admin(actor):
        return

    # ¿Existe la división?
    row = db.execute(
        select(Division.Id, Division.ServicioId)
        .where(Division.Id == int(division_id))
        .limit(1)
    ).first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Inmueble/División no encontrado",
        )

    dv_servicio_id = int(row[1]) if row[1] is not None else None
    if dv_servicio_id is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "El inmueble no tiene ServicioId asociado.",
                "division_id": int(division_id),
            },
        )

    actor_servicios = _get_actor_servicio_ids(db, actor.id)

    if dv_servicio_id in actor_servicios:
        return

    raise HTTPException(
        status_code=403,
        detail={
            "code": "forbidden_scope",
            "msg": "No puedes operar sobre este inmueble/división (fuera de tu alcance).",
            "division_id": int(division_id),
            "ServicioId": dv_servicio_id,
        },
    )


# ─────────────────────────────────────────────
# Scope: Unidad
# ─────────────────────────────────────────────

def ensure_actor_can_touch_unidad(
    db: Session,
    actor: UserPublic,
    unidad_id: int,
) -> None:
    """
    Validación mínima para operar sobre una unidad.

    Reglas:
    ✅ ADMIN: todo
    ❌ No-admin: BLOQUEADO (fail-closed)

    Nota: como en tu modelo la unidad cuelga del inmueble,
    el control real se hace vía ensure_actor_can_edit_division.
    """

    if is_admin(actor):
        return

    raise HTTPException(
        status_code=403,
        detail={
            "code": "forbidden_scope",
            "msg": "No puedes operar sobre unidades (solo administrador).",
            "unidad_id": int(unidad_id),
        },
    )
