# app/api/v1/division_sistemas.py
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.division_sistemas import DivisionSistemasDTO, DivisionSistemasUpdate
from app.services.division_sistemas_service import DivisionSistemasService

# ✅ Ajusta imports según tus modelos reales:
# Si tu tabla puente se llama distinto, cámbiala aquí.
try:
    from app.db.models.usuarios_divisiones import UsuarioDivision  # type: ignore
except Exception:  # pragma: no cover
    UsuarioDivision = None  # fallback si el modelo aún no existe/importa

router = APIRouter(prefix="/api/v1/divisiones", tags=["Sistemas por División"])
svc = DivisionSistemasService()
Log = logging.getLogger(__name__)

# ✅ Roles que pueden ESCRIBIR configuración de sistemas por división
DIVISION_SISTEMAS_WRITE_ROLES = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_FLOTA",
    "GESTOR_SERVICIO",
    # agrega aquí otros si aplica (pero NO metas roles de consulta)
)

def _has_role(u: UserPublic | None, role: str) -> bool:
    return bool(u and (u.roles or []) and role in (u.roles or []))

def ensure_actor_can_edit_division(db: Session, actor: UserPublic, division_id: int) -> None:
    """
    ADMIN: puede todo
    Gestores: solo pueden editar divisiones dentro de su alcance.

    Alcance implementado (mínimo seguro):
      - Si existe tabla puente usuarios_divisiones, se valida UsuarioDivision(UsuarioId, DivisionId)

    Si tu alcance real es por servicios/unidades, lo ajustamos (pero esto ya corta el 403 injusto,
    y evita abrir todo).
    """
    if _has_role(actor, "ADMINISTRADOR"):
        return

    # Si no tenemos modelo de puente importable, no podemos verificar scope -> bloquea por seguridad.
    if UsuarioDivision is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar el alcance del gestor (modelo UsuarioDivision no disponible).",
                "division_id": division_id,
            },
        )

    # ✅ Validación por vínculo directo usuario<->division
    exists = db.execute(
        select(UsuarioDivision.DivisionId).where(
            UsuarioDivision.UsuarioId == actor.id,
            UsuarioDivision.DivisionId == division_id,
        )
    ).first()

    if exists:
        return

    # ------------------------------------------------------------------
    # 🔧 EXTENSIÓN FUTURA (si tu alcance es por unidades/servicios):
    # - Por servicios: UsuarioServicio -> Unidad/Division (join)
    # - Por unidades: UsuarioUnidad -> Unidad -> DivisionUnidad (join)
    # Si me pasas esos modelos/relaciones lo cierro exacto.
    # ------------------------------------------------------------------

    raise HTTPException(
        status_code=403,
        detail={
            "code": "forbidden_scope",
            "msg": "No puedes modificar esta división (fuera de tu alcance).",
            "division_id": division_id,
        },
    )


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
    u: Annotated[UserPublic, Depends(require_roles(*DIVISION_SISTEMAS_WRITE_ROLES))] = None,
):
    # ✅ scope: admin todo, gestor solo sus divisiones
    if not u:
        raise HTTPException(status_code=401, detail="Unauthorized")

    ensure_actor_can_edit_division(db, u, division_id)

    updated = svc.update(
        db,
        division_id,
        payload=payload.model_dump(exclude_unset=True),
        user=getattr(u, "Username", None) if u else None,
    )

    Log.info(
        "PUT division_sistemas ok division_id=%s actor_id=%s roles=%s",
        division_id, getattr(u, "id", None), getattr(u, "roles", None),
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
