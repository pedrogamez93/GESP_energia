from __future__ import annotations

import logging
from typing import Annotated, List, Tuple, Optional, TypeAlias

from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.medidor import (
    MedidorDTO,
    MedidorListDTO,
    MedidorCreate,
    MedidorUpdate,
    MedidorPage,
)
from app.services.medidor_service import MedidorService

router = APIRouter(prefix="/api/v1/medidores", tags=["Medidores"])
svc = MedidorService()
DbDep: TypeAlias = Annotated[Session, Depends(get_db)]
Log = logging.getLogger(__name__)

# ==========================================================
# ✅ ROLES
#   - LECTURA: incluye GESTOR DE CONSULTA
#   - ESCRITURA: NO incluye GESTOR DE CONSULTA
# ==========================================================
MEDIDORES_READ_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_FLOTA",
    "GESTOR_SERVICIO",
    "GESTOR DE CONSULTA",
)

MEDIDORES_WRITE_ROLES: Tuple[str, ...] = (
    "ADMINISTRADOR",
    "GESTOR_UNIDAD",
    "GESTOR_FLOTA",
    "GESTOR_SERVICIO",
)

ReadUserDep = Annotated[UserPublic, Depends(require_roles(*MEDIDORES_READ_ROLES))]
WriteUserDep = Annotated[UserPublic, Depends(require_roles(*MEDIDORES_WRITE_ROLES))]

# ==========================================================
# ✅ SCOPES (tablas puente)
#   - UsuarioDivision: limita qué Divisiones puede ver un usuario
#   - MedidorDivision: puente dbo.MedidorDivision (DivisionId, MedidorId)
#   - Compra / CompraMedidor: si existen para validar /by-compra
# ==========================================================

try:
    from app.db.models.usuarios_divisiones import UsuarioDivision  # type: ignore
except Exception:
    UsuarioDivision = None  # type: ignore

try:
    # OJO: este import debe apuntar al archivo real donde definiste el modelo MedidorDivision
    from app.db.models.medidor_division import MedidorDivision  # type: ignore
except Exception:
    MedidorDivision = None  # type: ignore

try:
    from app.db.models.compra import Compra  # type: ignore
except Exception:
    Compra = None  # type: ignore

try:
    from app.db.models.compra_medidor import CompraMedidor  # type: ignore
except Exception:
    CompraMedidor = None  # type: ignore


def _is_admin(u: UserPublic) -> bool:
    return "ADMINISTRADOR" in (u.roles or [])


def _ensure_scope_model_or_forbid(model, code: str, msg: str, extra: dict) -> None:
    if model is None:
        raise HTTPException(
            status_code=403,
            detail={"code": code, "msg": msg, **extra},
        )


def _ensure_actor_can_access_division(db: Session, actor: UserPublic, division_id: int) -> None:
    """
    ADMIN: ok.
    No-admin: la division_id debe estar en UsuarioDivision.
    """
    if _is_admin(actor):
        return

    _ensure_scope_model_or_forbid(
        UsuarioDivision,
        "forbidden_scope",
        "No se puede verificar alcance (UsuarioDivision no disponible).",
        {"division_id": int(division_id)},
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
    Para listados, si NO es admin exigimos DivisionId
    (evita que un gestor consulte TODO el universo).
    """
    if division_id is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "missing_division", "msg": "DivisionId es requerido para tu rol."},
        )
    return int(division_id)


def _resolve_division_ids_for_medidor(db: Session, medidor_id: int) -> list[int]:
    """
    Devuelve las DivisionId asociadas a un MedidorId desde dbo.MedidorDivision.
    """
    _ensure_scope_model_or_forbid(
        MedidorDivision,
        "forbidden_scope",
        "No se puede verificar alcance por medidor (MedidorDivision no disponible).",
        {"medidor_id": int(medidor_id)},
    )

    rows = db.execute(
        select(MedidorDivision.DivisionId)
        .where(MedidorDivision.MedidorId == int(medidor_id))
    ).all()

    return [int(r[0]) for r in rows if r and r[0] is not None]


def _ensure_actor_can_access_medidor(db: Session, actor: UserPublic, medidor_id: int) -> None:
    """
    ADMIN: ok.
    No-admin: el medidor debe estar asociado a al menos una división del actor.
    """
    if _is_admin(actor):
        return

    divs = _resolve_division_ids_for_medidor(db, int(medidor_id))
    if not divs:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden_scope",
                "msg": "No se puede validar alcance del medidor (sin divisiones asociadas).",
                "medidor_id": int(medidor_id),
            },
        )

    # Debe tener acceso a al menos una división del medidor
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
            "msg": "No tienes acceso a este medidor (fuera de tus divisiones).",
            "medidor_id": int(medidor_id),
        },
    )


def _ensure_actor_can_access_compra(db: Session, actor: UserPublic, compra_id: int) -> None:
    """
    Valida alcance para endpoints que consultan por compra:
    - Caso A: Compra.DivisionId existe => valida esa división.
    - Caso B: CompraMedidor existe => valida al menos un medidor accesible en la compra.
    """
    if _is_admin(actor):
        return

    # Caso A: Compra.DivisionId
    if Compra is not None and hasattr(Compra, "DivisionId"):
        row = db.execute(
            select(getattr(Compra, "DivisionId")).where(Compra.Id == int(compra_id))
        ).first()
        div = int(row[0]) if row and row[0] is not None else None
        if div is None:
            raise HTTPException(
                status_code=403,
                detail={"code": "forbidden_scope", "msg": "Compra sin DivisionId.", "compra_id": int(compra_id)},
            )
        _ensure_actor_can_access_division(db, actor, int(div))
        return

    # Caso B: CompraMedidor -> MedidorDivision
    _ensure_scope_model_or_forbid(
        CompraMedidor,
        "forbidden_scope",
        "No se puede verificar alcance por compra (CompraMedidor no disponible).",
        {"compra_id": int(compra_id)},
    )

    med_rows = db.execute(
        select(CompraMedidor.MedidorId).where(CompraMedidor.CompraId == int(compra_id))
    ).all()
    med_ids = [int(r[0]) for r in med_rows if r and r[0] is not None]

    if not med_ids:
        raise HTTPException(
            status_code=403,
            detail={"code": "forbidden_scope", "msg": "Compra sin medidores.", "compra_id": int(compra_id)},
        )

    # Al menos uno accesible (flexible)
    for mid in med_ids:
        try:
            _ensure_actor_can_access_medidor(db, actor, int(mid))
            return
        except HTTPException:
            continue

    raise HTTPException(
        status_code=403,
        detail={"code": "forbidden_scope", "msg": "Fuera de tu alcance (compra).", "compra_id": int(compra_id)},
    )


# ==========================================================
# GETs (LECTURA con scope)
# ==========================================================

@router.get(
    "",
    response_model=MedidorPage,
    summary="Listado paginado de medidores",
)
def list_medidores(
    db: DbDep,
    u: ReadUserDep,
    q: str | None = Query(default=None, description="Busca por Número / Nombre cliente"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    NumeroClienteId: int | None = Query(default=None),
    DivisionId: int | None = Query(default=None),
    institucion_id: int | None = Query(default=None),
    servicio_id: int | None = Query(default=None),
    active: bool | None = Query(default=None),
    medidor_id: int | None = Query(default=None, ge=1),
):
    # 🔒 No-admin: exige DivisionId y valida scope
    if not _is_admin(u):
        div_id = _require_division_for_non_admin(u, DivisionId)
        _ensure_actor_can_access_division(db, u, div_id)
        DivisionId = div_id
    else:
        # ✅ Admin: si viene DivisionId, también podemos filtrar y proteger performance
        if DivisionId is not None:
            DivisionId = int(DivisionId)

    return svc.list(
        db=db,
        q=q,
        page=page,
        page_size=page_size,
        numero_cliente_id=NumeroClienteId,
        division_id=DivisionId,
        institucion_id=institucion_id,
        servicio_id=servicio_id,
        active=active,
        medidor_id=medidor_id,
    )


@router.get(
    "/division/{division_id}",
    response_model=List[MedidorListDTO],
    summary="Medidores por división",
)
def list_by_division(
    db: DbDep,
    u: ReadUserDep,
    division_id: Annotated[int, Path(..., ge=1)],
):
    _ensure_actor_can_access_division(db, u, int(division_id))
    items = svc.by_division(db, int(division_id))
    return [MedidorListDTO.model_validate(x) for x in items]


@router.get(
    "/numero-cliente/{numero_cliente_id}",
    response_model=List[MedidorListDTO],
    summary="Medidores por NúmeroClienteId",
)
def list_by_numero_cliente(
    db: DbDep,
    u: ReadUserDep,
    numero_cliente_id: Annotated[int, Path(..., ge=1)],
):
    items = svc.by_numero_cliente(db, int(numero_cliente_id))

    # 🔒 No-admin: valida que exista al menos un medidor accesible
    if not _is_admin(u):
        ok_any = False
        for it in items:
            mid = int(getattr(it, "Id", None) or getattr(it, "id", None) or 0)
            if mid:
                try:
                    _ensure_actor_can_access_medidor(db, u, mid)
                    ok_any = True
                    break
                except HTTPException:
                    continue
        if not ok_any:
            raise HTTPException(status_code=403, detail={"code": "forbidden_scope", "msg": "Fuera de tu alcance."})

    return [MedidorListDTO.model_validate(x) for x in items]


@router.get(
    "/{medidor_id}",
    response_model=MedidorDTO,
    summary="Detalle de un medidor",
)
def get_medidor(
    db: DbDep,
    u: ReadUserDep,
    medidor_id: Annotated[int, Path(..., ge=1)],
):
    _ensure_actor_can_access_medidor(db, u, int(medidor_id))
    obj = svc.get(db, int(medidor_id))
    if not obj:
        raise HTTPException(status_code=404, detail="Medidor no encontrado")
    return obj


@router.get(
    "/{medidor_id}/detalle",
    summary="Detalle completo de medidor (institución, servicio, dirección)",
)
def get_medidor_detalle_completo(
    db: DbDep,
    u: ReadUserDep,
    medidor_id: Annotated[int, Path(..., ge=1)],
):
    _ensure_actor_can_access_medidor(db, u, int(medidor_id))
    return svc.get_detalle_completo(db, int(medidor_id))


@router.get(
    "/buscar",
    response_model=MedidorDTO,
    summary="Buscar por NumeroClienteId y NumMedidor",
)
def find_by_num_cliente_and_numero(
    db: DbDep,
    u: ReadUserDep,
    numeroClienteId: int = Query(..., ge=1),
    numMedidor: str = Query(..., min_length=1),
):
    obj = svc.by_numcliente_and_numero(db, int(numeroClienteId), numMedidor)
    if not obj:
        raise HTTPException(status_code=404, detail="Medidor no encontrado")

    mid = int(getattr(obj, "Id", None) or getattr(obj, "id", None) or 0)
    if mid:
        _ensure_actor_can_access_medidor(db, u, mid)
    return obj


@router.get(
    "/para-compra/by-num-cliente/{num_cliente_id}/by-division/{division_id}",
    response_model=List[MedidorListDTO],
    summary="Medidores habilitados para compra por (NumeroClienteId, DivisionId)",
)
def for_compra(
    db: DbDep,
    u: ReadUserDep,
    num_cliente_id: Annotated[int, Path(..., ge=1)],
    division_id: Annotated[int, Path(..., ge=1)],
):
    _ensure_actor_can_access_division(db, u, int(division_id))
    items = svc.for_compra_by_numcliente_division(db, int(num_cliente_id), int(division_id))
    return [MedidorListDTO.model_validate(x) for x in items]


@router.get(
    "/by-compra/{compra_id}",
    response_model=List[MedidorListDTO],
    summary="Medidores asociados a una compra",
)
def by_compra(
    db: DbDep,
    u: ReadUserDep,
    compra_id: Annotated[int, Path(..., ge=1)],
):
    _ensure_actor_can_access_compra(db, u, int(compra_id))
    items = svc.by_compra(db, int(compra_id))
    return [MedidorListDTO.model_validate(x) for x in items]


@router.post(
    "/check-exist-medidor",
    response_model=MedidorDTO,
    summary="Verifica existencia por (NumeroClienteId, Numero [, DivisionId])",
)
def check_exist_medidor(
    db: DbDep,
    u: ReadUserDep,
    payload: dict,
):
    try:
        numero_cliente_id = int(payload.get("NumeroClienteId"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="NumeroClienteId inválido")

    numero = str(payload.get("Numero", "")).strip()

    division_val = payload.get("DivisionId")
    try:
        division_id = int(division_val) if division_val is not None else None
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="DivisionId inválido")

    # 🔒 No-admin: exige DivisionId + scope
    if not _is_admin(u):
        div_id = _require_division_for_non_admin(u, division_id)
        _ensure_actor_can_access_division(db, u, div_id)
        division_id = div_id

    found = svc.check_exist(db, numero_cliente_id, numero, division_id)
    if not found:
        raise HTTPException(status_code=404, detail="No existe el medidor con esos parámetros")

    mid = int(getattr(found, "Id", None) or getattr(found, "id", None) or 0)
    if mid:
        _ensure_actor_can_access_medidor(db, u, mid)
    return found


# ==========================================================
# ESCRITURAS (ADMINISTRADOR + GESTORES) -> con scope
# ==========================================================

@router.post(
    "",
    response_model=MedidorDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMINISTRADOR/GESTORES) Crear medidor",
)
def create_medidor(
    db: DbDep,
    payload: MedidorCreate,
    current_user: WriteUserDep,
):
    # Nota: aquí lo ideal es que el service "create" determine la(s) divisiones
    # asociadas y validarlas. Si el create NO asocia divisiones, no hay scope que validar.
    return svc.create(db, payload, created_by=current_user.id)


@router.put(
    "/{medidor_id}",
    response_model=MedidorDTO,
    summary="(ADMINISTRADOR/GESTORES) Actualizar medidor",
)
def update_medidor(
    db: DbDep,
    medidor_id: Annotated[int, Path(..., ge=1)],
    payload: MedidorUpdate,
    current_user: WriteUserDep,
):
    _ensure_actor_can_access_medidor(db, current_user, int(medidor_id))
    return svc.update(db, int(medidor_id), payload, modified_by=current_user.id)


@router.delete(
    "/{medidor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMINISTRADOR/GESTORES) Eliminar medidor (hard delete)",
)
def delete_medidor(
    db: DbDep,
    medidor_id: Annotated[int, Path(..., ge=1)],
    current_user: WriteUserDep,
):
    _ensure_actor_can_access_medidor(db, current_user, int(medidor_id))
    svc.delete(db, int(medidor_id))
    return None


@router.put(
    "/{medidor_id}/divisiones",
    response_model=List[int],
    summary="(ADMINISTRADOR/GESTORES) Reemplaza divisiones asociadas al medidor (tabla puente)",
)
def set_divisiones(
    db: DbDep,
    medidor_id: Annotated[int, Path(..., ge=1)],
    division_ids: List[int],
    current_user: WriteUserDep,
):
    # Gestor solo puede asociar a divisiones dentro de su alcance
    if not _is_admin(current_user):
        for d in division_ids:
            _ensure_actor_can_access_division(db, current_user, int(d))

    return svc.set_divisiones(db, int(medidor_id), division_ids, actor_id=current_user.id)
