from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, Path, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.medidor_vinculo import IdsPayload, MedidorMiniDTO
from app.services.medidor_vinculo_service import MedidorVinculoService

router = APIRouter(prefix="/api/v1/medidores", tags=["Medidores"])
svc = MedidorVinculoService()
DbDep = Annotated[Session, Depends(get_db)]

# ==========================================================
# Roles
# ==========================================================
MEDIDORES_VINCULO_READ_ROLES = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_SERVICIO",
    "GESTOR_FLOTA",
    "GESTOR DE CONSULTA",
)

# ⚠️ Escritura: igual que venimos haciendo en los otros módulos:
# - Admin + gestores operativos
# - NO incluye gestor consulta
MEDIDORES_VINCULO_WRITE_ROLES = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_SERVICIO",
    "GESTOR_FLOTA",
)

ReadUser = Annotated[UserPublic, Depends(require_roles(*MEDIDORES_VINCULO_READ_ROLES))]
WriteUser = Annotated[UserPublic, Depends(require_roles(*MEDIDORES_VINCULO_WRITE_ROLES))]

# ==========================================================
# Scope por división (UsuarioDivision) para proteger consultas
# ==========================================================
try:
    from app.db.models.usuarios_divisiones import UsuarioDivision  # type: ignore
except Exception:
    UsuarioDivision = None  # type: ignore


def _is_admin(u: UserPublic) -> bool:
    return "ADMINISTRADOR" in (u.roles or [])


def _ensure_actor_can_access_division(db: Session, actor: UserPublic, division_id: int) -> None:
    """
    ADMIN: ok.
    No-admin: DivisionId debe estar en UsuarioDivision.
    Si no existe UsuarioDivision, por seguridad -> 403.
    """
    if _is_admin(actor):
        return

    if UsuarioDivision is None:
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
        ).limit(1)
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


# ==========================================================
# Consultas (READ) - incluyen gestor consulta, pero SCOPED
# ==========================================================
@router.get(
    "/por-division/{division_id}",
    response_model=List[MedidorMiniDTO],
    summary="Lista medidores asociados a una división (vía tabla N-N) (scoped)",
)
def medidores_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: ReadUser,
):
    _ensure_actor_can_access_division(db, current_user, int(division_id))
    items = svc.medidores_por_division(db, int(division_id))
    return [MedidorMiniDTO.model_validate(x) for x in items]


@router.get(
    "/por-numero-cliente/{num_cliente_id}",
    response_model=List[MedidorMiniDTO],
    summary="Lista medidores por NumeroClienteId (scoped por al menos una división del usuario)",
)
def medidores_por_numero_cliente(
    num_cliente_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: ReadUser,
):
    # ⚠️ Este endpoint no trae DivisionId, entonces:
    # - ADMIN: puede ver todos
    # - No-admin: devolvemos SOLO lo que esté dentro de sus divisiones (ideal en el service)
    #
    # Aquí hacemos defensa mínima:
    # 1) Si el service ya tiene un método scoped, úsalo
    # 2) Si no, fallback: traemos todo y filtramos por divisiones usando la tabla puente MedidorDivision,
    #    pero si eso no existe, bloqueamos para evitar fuga.
    if _is_admin(current_user):
        items = svc.medidores_por_numero_cliente(db, int(num_cliente_id))
        return [MedidorMiniDTO.model_validate(x) for x in items]

    # Preferimos método scoped si existe (recomendado)
    if hasattr(svc, "medidores_por_numero_cliente_scoped"):
        items = svc.medidores_por_numero_cliente_scoped(db, int(num_cliente_id), actor=current_user)
        return [MedidorMiniDTO.model_validate(x) for x in items]

    # Fallback seguro: filtrar por MedidorDivision + UsuarioDivision
    try:
        from app.db.models.medidor_division import MedidorDivision  # type: ignore
    except Exception:
        MedidorDivision = None  # type: ignore

    if UsuarioDivision is None or MedidorDivision is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede aplicar scope sin UsuarioDivision/MedidorDivision. Implementa método scoped en el service.",
            },
        )

    # Trae todos y luego filtra por divisiones del actor (sin abrir fuga)
    raw = svc.medidores_por_numero_cliente(db, int(num_cliente_id))
    if not raw:
        return []

    # divisiones del actor
    div_rows = db.execute(
        select(UsuarioDivision.DivisionId).where(UsuarioDivision.UsuarioId == current_user.id)
    ).all()
    actor_divs = {int(r[0]) for r in div_rows if r and r[0] is not None}
    if not actor_divs:
        return []

    # medidor -> divisiones
    # (OJO: esto asume que MedidorMiniDTO tiene Id; si no, ajusta getattr)
    out: list[MedidorMiniDTO] = []
    for m in raw:
        mid = int(getattr(m, "Id", None) or getattr(m, "id", None) or 0)
        if not mid:
            continue
        rows = db.execute(select(MedidorDivision.DivisionId).where(MedidorDivision.MedidorId == mid)).all()
        md_divs = {int(r[0]) for r in rows if r and r[0] is not None}
        if md_divs.intersection(actor_divs):
            out.append(MedidorMiniDTO.model_validate(m))

    return out


# ==========================================================
# Escrituras (ADMIN + gestores operativos) - NO consulta
# ==========================================================
@router.put(
    "/{medidor_id}/divisiones",
    response_model=List[int],
    summary="(ADMINISTRADOR/GESTOR_*) Reemplaza divisiones asociadas al medidor (tabla N-N)",
)
def set_divisiones_para_medidor(
    medidor_id: Annotated[int, Path(..., ge=1)],
    payload: IdsPayload | None,
    db: DbDep,
    current_user: WriteUser,
):
    ids = payload.Ids if payload else []

    # 🔒 Gestores: solo pueden asociar a divisiones dentro de su alcance
    if not _is_admin(current_user):
        for d in ids:
            _ensure_actor_can_access_division(db, current_user, int(d))

    return svc.set_divisiones_para_medidor(db, int(medidor_id), [int(x) for x in ids])
