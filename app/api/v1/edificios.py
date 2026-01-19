# app/api/v1/edificios.py
from __future__ import annotations

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query, Path, status, Response, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.edificio import (
    EdificioDTO, EdificioListDTO, EdificioSelectDTO,
    EdificioCreate, EdificioUpdate,
)
from app.services.edificio_service import EdificioService
from app.db.models.edificio import Edificio  # ✅ para validar comuna en create (si aplica)

router = APIRouter(prefix="/api/v1/edificios", tags=["Edificios"])
svc = EdificioService()
DbDep = Annotated[Session, Depends(get_db)]
Log = logging.getLogger(__name__)

# ✅ Roles de escritura (igual que tus otros módulos)
EDIFICIOS_WRITE_ROLES = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_SERVICIO",
    "GESTOR_FLOTA",
)

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
    Si faltan modelos para scope, por seguridad no dejamos operar a gestores.
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
    """
    Protege contra casos donde el modelo existe pero no tiene la columna.
    """
    return Division is not None and hasattr(Division, field)


def _ensure_actor_can_edit_edificio(db: Session, actor: UserPublic, edificio_id: int) -> None:
    """
    ADMIN: puede editar cualquier edificio.
    Gestores: pueden editar SOLO edificios donde tengan al menos una División en su alcance,
             y esa División pertenezca a ese edificio.

    Requiere:
      - UsuarioDivision(UsuarioId, DivisionId)
      - Division(Id, EdificioId)

    Si faltan modelos/columnas, por seguridad devolvemos 403.
    """
    if _is_admin(actor):
        return

    _ensure_scope_models_or_forbid("edificio")
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
                "msg": "No puedes modificar este edificio (fuera de tu alcance).",
                "edificio_id": int(edificio_id),
            },
        )


def _ensure_actor_can_create_edificio(db: Session, actor: UserPublic, comuna_id: int | None) -> None:
    """
    Crear edificio es delicado: Edificio no tiene ServicioId/InstitucionId.
    Opción segura para gestores:
      - Permitimos crear solo si el gestor ya tiene alcance en esa comuna
        (es decir, tiene al menos una Division en su scope dentro de un edificio de esa comuna).

    Si no hay comuna_id -> solo ADMIN.
    Si no hay modelos/columnas para resolver -> solo ADMIN.
    """
    if _is_admin(actor):
        return

    if comuna_id is None:
        raise HTTPException(
            status_code=403,
            detail={"code": "forbidden", "msg": "Para crear edificio debes indicar ComunaId (solo gestores)."},
        )

    # Si no podemos verificar scope real, no abrimos creación
    _ensure_scope_models_or_forbid("create_edificio")

    # Necesitamos Division.EdificioId para llegar a Edificio.ComunaId
    if not _division_has_field("EdificioId"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede verificar alcance para crear (Division.EdificioId no disponible). Solo ADMIN puede crear.",
            },
        )

    # ¿El gestor tiene alguna división en su alcance cuya división pertenezca a un edificio en esa comuna?
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


# --- GET (con token cualquiera) ---
@router.get(
    "",
    response_model=List[EdificioListDTO],
    summary="Listado paginado (headers) de edificios",
    dependencies=[Depends(require_roles("*"))],
)
def list_edificios(
    response: Response,
    db: DbDep,
    q: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    ComunaId: int | None = Query(default=None),
    active: bool | None = Query(default=True),
):
    res = svc.list(db, q, page, page_size, ComunaId, active)
    total = res["total"]
    size = res["page_size"]
    curr = res["page"]
    total_pages = (total + size - 1) // size if size else 1

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(curr)
    response.headers["X-Page-Size"] = str(size)
    response.headers["X-Total-Pages"] = str(total_pages)

    return [EdificioListDTO.model_validate(x) for x in res["items"]]


@router.get(
    "/select",
    response_model=List[EdificioSelectDTO],
    summary="Select (Id, Nombre) solo activos",
    dependencies=[Depends(require_roles("*"))],
)
def select_edificios(
    db: DbDep,
    q: str | None = Query(default=None),
    ComunaId: int | None = Query(default=None),
):
    rows = svc.list_select(db, q, ComunaId)
    return [EdificioSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]


@router.get(
    "/{id}",
    response_model=EdificioDTO,
    summary="Detalle de edificio",
    dependencies=[Depends(require_roles("*"))],
)
def get_edificio(
    id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.get(db, id)


# --- ESCRITURAS (ADMIN + gestores con scope) ---
@router.post(
    "",
    response_model=EdificioDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear edificio (ADMINISTRADOR | GESTOR_* con scope por comuna)",
)
def create_edificio(
    payload: EdificioCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles(*EDIFICIOS_WRITE_ROLES))],
):
    # ✅ ahora sí permitimos gestores, pero solo si tienen scope en esa comuna
    _ensure_actor_can_create_edificio(db, current_user, payload.ComunaId)

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
    current_user: Annotated[UserPublic, Depends(require_roles(*EDIFICIOS_WRITE_ROLES))],
):
    _ensure_actor_can_edit_edificio(db, current_user, int(id))
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
    current_user: Annotated[UserPublic, Depends(require_roles(*EDIFICIOS_WRITE_ROLES))],
):
    _ensure_actor_can_edit_edificio(db, current_user, int(id))
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
    current_user: Annotated[UserPublic, Depends(require_roles(*EDIFICIOS_WRITE_ROLES))],
):
    _ensure_actor_can_edit_edificio(db, current_user, int(id))
    obj = svc.reactivate(db, int(id), modified_by=current_user.id)
    return obj
