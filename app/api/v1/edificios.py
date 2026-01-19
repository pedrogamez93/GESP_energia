# app/api/v1/edificios.py
from __future__ import annotations

import logging
from typing import Annotated, List, Tuple

from fastapi import APIRouter, Depends, Query, Path, status, Response, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.edificio import (
    EdificioDTO,
    EdificioListDTO,
    EdificioSelectDTO,
    EdificioCreate,
    EdificioUpdate,
)
from app.services.edificio_service import EdificioService
from app.db.models.edificio import Edificio  # ✅ para join a comuna en create scope (si aplica)

router = APIRouter(prefix="/api/v1/edificios", tags=["Edificios"])
svc = EdificioService()
DbDep = Annotated[Session, Depends(get_db)]
Log = logging.getLogger(__name__)

# ==========================================================
# ✅ ROLES
#   - LECTURA: incluye GESTOR DE CONSULTA
#   - ESCRITURA: NO incluye GESTOR DE CONSULTA
# ==========================================================
EDIFICIOS_READ_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_SERVICIO",
    "GESTOR_FLOTA",
    "GESTOR DE CONSULTA",
)

EDIFICIOS_WRITE_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_SERVICIO",
    "GESTOR_FLOTA",
)

ReadUserDep = Annotated[UserPublic, Depends(require_roles(*EDIFICIOS_READ_ROLES))]
WriteUserDep = Annotated[UserPublic, Depends(require_roles(*EDIFICIOS_WRITE_ROLES))]

# ─────────────────────────────────────────────────────────────
# Scopes (si existen en tu proyecto)
# ─────────────────────────────────────────────────────────────
try:
    from app.db.models.usuarios_divisiones import UsuarioDivision  # type: ignore
except Exception:
    UsuarioDivision = None  # type: ignore

try:
    from app.db.models.division import Division  # type: ignore
except Exception:
    Division = None  # type: ignore


def _is_admin(user: UserPublic) -> bool:
    return "ADMINISTRADOR" in (user.roles or [])


def _ensure_scope_models_or_forbid(kind: str) -> None:
    """
    Si faltan modelos para scope, por seguridad no dejamos operar a no-admin.
    """
    if UsuarioDivision is None or Division is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": f"No se puede verificar alcance ({kind}) (UsuarioDivision/Division no disponible).",
            },
        )


def _division_has_field(field: str) -> bool:
    return Division is not None and hasattr(Division, field)


def _ensure_actor_can_access_edificio(db: Session, actor: UserPublic, edificio_id: int) -> None:
    """
    ADMIN: ok.
    No-admin: debe tener al menos una división en su scope perteneciente a ese edificio.

    Requiere:
      - UsuarioDivision(UsuarioId, DivisionId)
      - Division(Id, EdificioId)
    """
    if _is_admin(actor):
        return

    _ensure_scope_models_or_forbid("edificio_access")
    if not _division_has_field("EdificioId"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar alcance (Division.EdificioId no disponible).",
                "edificio_id": int(edificio_id),
            },
        )

    ok = db.execute(
        select(Division.Id)
        .join(UsuarioDivision, UsuarioDivision.DivisionId == Division.Id)
        .where(
            UsuarioDivision.UsuarioId == actor.id,
            getattr(Division, "EdificioId") == int(edificio_id),
        )
        .limit(1)
    ).first()

    if not ok:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No tienes acceso a este edificio (fuera de tu alcance).",
                "edificio_id": int(edificio_id),
            },
        )


def _ensure_actor_can_create_edificio(db: Session, actor: UserPublic, comuna_id: int | None) -> None:
    """
    Crear edificio es sensible (Edificio no cuelga directo de División).
    Política segura:
      - ADMIN: ok.
      - No-admin: solo si indica ComunaId y el usuario ya tiene alguna división en su scope
                 cuyo edificio actual pertenezca a esa comuna (proxy de alcance territorial).

    Si no hay ComunaId -> solo ADMIN.
    Si no podemos verificar scope -> solo ADMIN.
    """
    if _is_admin(actor):
        return

    if comuna_id is None:
        raise HTTPException(
            status_code=403,
            detail={"code": "forbidden", "msg": "Para crear edificio debes indicar ComunaId (solo gestores)."},
        )

    _ensure_scope_models_or_forbid("create_edificio")

    if not _division_has_field("EdificioId"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar alcance para crear (Division.EdificioId no disponible). Solo ADMIN puede crear.",
            },
        )

    ok = db.execute(
        select(Division.Id)
        .join(UsuarioDivision, UsuarioDivision.DivisionId == Division.Id)
        .join(Edificio, Edificio.Id == getattr(Division, "EdificioId"))
        .where(
            UsuarioDivision.UsuarioId == actor.id,
            Edificio.ComunaId == int(comuna_id),
        )
        .limit(1)
    ).first()

    if not ok:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No puedes crear edificios en esta comuna (fuera de tu alcance).",
                "ComunaId": int(comuna_id),
            },
        )


# ==========================================================
# GET (lectura + scope)
# ==========================================================
@router.get(
    "",
    response_model=List[EdificioListDTO],
    summary="Listado paginado (headers) de edificios",
)
def list_edificios(
    response: Response,
    db: DbDep,
    u: ReadUserDep,
    q: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    ComunaId: int | None = Query(default=None),
    active: bool | None = Query(default=True),
):
    # 🔒 Si no es admin, exigimos ComunaId (o se vuelve “listado global”).
    if not _is_admin(u) and ComunaId is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "missing_comuna", "msg": "ComunaId es requerido para tu rol."},
        )

    res = svc.list(db, q, page, page_size, ComunaId, active)

    total = int(res["total"])
    size = int(res["page_size"])
    curr = int(res["page"])
    total_pages = (total + size - 1) // size if size else 1

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(curr)
    response.headers["X-Page-Size"] = str(size)
    response.headers["X-Total-Pages"] = str(total_pages)

    # 🔒 Si no es admin, filtramos por alcance edificio a edificio (seguro, aunque menos eficiente).
    items = res["items"]
    if not _is_admin(u):
        filtered: list = []
        for it in items:
            eid = int(getattr(it, "Id", None) or getattr(it, "id", None) or 0)
            if not eid:
                continue
            try:
                _ensure_actor_can_access_edificio(db, u, eid)
                filtered.append(it)
            except HTTPException:
                continue
        items = filtered

    return [EdificioListDTO.model_validate(x) for x in items]


@router.get(
    "/select",
    response_model=List[EdificioSelectDTO],
    summary="Select (Id, Nombre) solo activos",
)
def select_edificios(
    db: DbDep,
    u: ReadUserDep,
    q: str | None = Query(default=None),
    ComunaId: int | None = Query(default=None),
):
    if not _is_admin(u) and ComunaId is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "missing_comuna", "msg": "ComunaId es requerido para tu rol."},
        )

    rows = svc.list_select(db, q, ComunaId)

    # 🔒 Si no es admin, filtramos por alcance edificio a edificio
    if not _is_admin(u):
        out: list[EdificioSelectDTO] = []
        for r in rows:
            eid = int(r[0])
            try:
                _ensure_actor_can_access_edificio(db, u, eid)
                out.append(EdificioSelectDTO(Id=eid, Nombre=r[1]))
            except HTTPException:
                continue
        return out

    return [EdificioSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]


@router.get(
    "/{id}",
    response_model=EdificioDTO,
    summary="Detalle de edificio",
)
def get_edificio(
    id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    u: ReadUserDep,
):
    _ensure_actor_can_access_edificio(db, u, int(id))
    return svc.get(db, int(id))


# ==========================================================
# ESCRITURAS (ADMIN + gestores con scope)
# ==========================================================
@router.post(
    "",
    response_model=EdificioDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear edificio (ADMINISTRADOR | GESTOR_* con scope por comuna)",
)
def create_edificio(
    payload: EdificioCreate,
    db: DbDep,
    current_user: WriteUserDep,
):
    _ensure_actor_can_create_edificio(db, current_user, getattr(payload, "ComunaId", None))

    obj = svc.create(
        db,
        payload.model_dump(exclude_unset=True),
        created_by=current_user.id,
    )
    return obj


@router.put(
    "/{id}",
    response_model=EdificioDTO,
    summary="Actualizar edificio (ADMINISTRADOR | GESTOR_* con scope)",
)
def update_edificio(
    id: Annotated[int, Path(..., ge=1)],
    payload: EdificioUpdate,
    db: DbDep,
    current_user: WriteUserDep,
):
    _ensure_actor_can_access_edificio(db, current_user, int(id))
    obj = svc.update(
        db,
        int(id),
        payload.model_dump(exclude_unset=True),
        modified_by=current_user.id,
    )
    return obj


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar edificio (soft-delete) (ADMINISTRADOR | GESTOR_* con scope)",
)
def delete_edificio(
    id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: WriteUserDep,
):
    _ensure_actor_can_access_edificio(db, current_user, int(id))
    svc.soft_delete(db, int(id), modified_by=current_user.id)
    return None


@router.patch(
    "/{id}/reactivar",
    response_model=EdificioDTO,
    summary="Reactivar edificio (Active=True) (ADMINISTRADOR | GESTOR_* con scope)",
)
def reactivate_edificio(
    id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: WriteUserDep,
):
    _ensure_actor_can_access_edificio(db, current_user, int(id))
    obj = svc.reactivate(db, int(id), modified_by=current_user.id)
    return obj
