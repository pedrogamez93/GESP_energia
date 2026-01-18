from typing import Annotated, List, Optional, TypeAlias

from fastapi import APIRouter, Depends, Path, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.energetico_division import (
    EnergeticoDivisionDTO,
    EnergeticoDivisionReplacePayload,
    EnergeticoDivisionCreateItem,
)
from app.services.energetico_division_service import EnergeticoDivisionService

# ✅ Alias UnidadId -> DivisionId (UnidadesInmuebles.InmuebleId)
from app.services.unidad_scope import division_id_from_unidad

router = APIRouter(prefix="/api/v1/energetico-divisiones", tags=["EnergeticoDivision"])
svc = EnergeticoDivisionService()

DbDep: TypeAlias = Annotated[Session, Depends(get_db)]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_division_from_unidad_or_raise(db: Session, unidad_id: int) -> int:
    """
    Resuelve UnidadId -> DivisionId vía UnidadesInmuebles.InmuebleId.
    Lanza 404/400 según lo que haga division_id_from_unidad (idealmente 404 si no existe).
    """
    try:
        div = division_id_from_unidad(db, int(unidad_id))
        return int(div)
    except HTTPException:
        raise
    except Exception:
        # por si division_id_from_unidad no lanza HTTPException y viene algo raro
        raise HTTPException(status_code=404, detail={"code": "unidad_not_found", "msg": "UnidadId no encontrada"})


def _division_mismatch(unidad_id: int, division_id_given: int, division_id_from_unidad: int) -> None:
    raise HTTPException(
        status_code=400,
        detail={
            "code": "division_mismatch",
            "msg": "DivisionId no coincide con el inmueble de la unidad",
            "UnidadId": int(unidad_id),
            "DivisionId_given": int(division_id_given),
            "DivisionId_from_unidad": int(division_id_from_unidad),
        },
    )


# =========================
# GET: listado por división
# =========================
@router.get(
    "/division/{division_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="Listado por división",
)
def list_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.list_by_division(db, division_id)


# =========================
# ✅ GET: listado por unidad (ALIAS)
# =========================
@router.get(
    "/unidad/{unidad_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="Listado por unidad (alias: UnidadId -> DivisionId)",
)
def list_por_unidad(
    unidad_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    division_id = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    return svc.list_by_division(db, division_id)


# ==========================================
# GET: divisiones que usan un energético X
# ==========================================
@router.get(
    "/energetico/{energetico_id}/divisiones",
    response_model=List[int],
    summary="Divisiones que usan un energético",
)
def divisiones_por_energetico(
    energetico_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.list_divisiones_by_energetico(db, energetico_id)


# ==============================================================
# PUT: reemplazar set completo de energéticos para una división
# ==============================================================
@router.put(
    "/division/{division_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="(ADMINISTRADOR) Reemplaza set para una división",
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def replace_set(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionReplacePayload,
    db: DbDep,
):
    items = [it.model_dump() for it in (payload.items or [])]
    return svc.replace_for_division(db, division_id, items)


# ==============================================================
# ✅ PUT: reemplazar set completo por UNIDAD (ALIAS)
# ==============================================================
@router.put(
    "/unidad/{unidad_id}",
    response_model=List[EnergeticoDivisionDTO],
    summary="(ADMINISTRADOR) Reemplaza set para una unidad (alias UnidadId -> DivisionId)",
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def replace_set_por_unidad(
    unidad_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionReplacePayload,
    db: DbDep,
    # opcional: si el caller también manda DivisionId, validamos mismatch
    DivisionId: Optional[int] = Query(default=None, ge=1, description="Opcional: valida mismatch con UnidadId"),
):
    division_from_unidad = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    if DivisionId is not None and int(DivisionId) != int(division_from_unidad):
        _division_mismatch(int(unidad_id), int(DivisionId), int(division_from_unidad))

    items = [it.model_dump() for it in (payload.items or [])]
    return svc.replace_for_division(db, division_from_unidad, items)


# ==========================================
# POST: asignar energético a una división
# ==========================================
@router.post(
    "/division/{division_id}/assign",
    response_model=EnergeticoDivisionDTO,
    summary="(ADMINISTRADOR) Asignar un energético a la división",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def assign_energetico(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionCreateItem,  # EnergeticoId y NumeroClienteId
    db: DbDep,
):
    return svc.assign_to_division(
        db=db,
        division_id=division_id,
        energetico_id=payload.EnergeticoId,
        numero_cliente_id=payload.NumeroClienteId,
    )


# ==========================================
# ✅ POST: asignar energético a una UNIDAD (ALIAS)
# ==========================================
@router.post(
    "/unidad/{unidad_id}/assign",
    response_model=EnergeticoDivisionDTO,
    summary="(ADMINISTRADOR) Asignar un energético a la unidad (alias UnidadId -> DivisionId)",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def assign_energetico_unidad(
    unidad_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoDivisionCreateItem,
    db: DbDep,
    DivisionId: Optional[int] = Query(default=None, ge=1, description="Opcional: valida mismatch con UnidadId"),
):
    division_from_unidad = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    if DivisionId is not None and int(DivisionId) != int(division_from_unidad):
        _division_mismatch(int(unidad_id), int(DivisionId), int(division_from_unidad))

    return svc.assign_to_division(
        db=db,
        division_id=division_from_unidad,
        energetico_id=payload.EnergeticoId,
        numero_cliente_id=payload.NumeroClienteId,
    )


# ===============================================
# DELETE: desasignar energético de una división
# ===============================================
@router.delete(
    "/division/{division_id}/energetico/{energetico_id}",
    summary="(ADMINISTRADOR) Desasignar un energético de la división",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def unassign_energetico(
    division_id: Annotated[int, Path(..., ge=1)],
    energetico_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    numero_cliente_id: Optional[int] = Query(
        None, ge=1, description="Opcional: si se usó un NumeroClienteId en la asignación"
    ),
):
    _ = svc.unassign_from_division(
        db=db,
        division_id=division_id,
        energetico_id=energetico_id,
        numero_cliente_id=numero_cliente_id,
    )
    return None


# ===============================================
# ✅ DELETE: desasignar energético de una UNIDAD (ALIAS)
# ===============================================
@router.delete(
    "/unidad/{unidad_id}/energetico/{energetico_id}",
    summary="(ADMINISTRADOR) Desasignar un energético de la unidad (alias UnidadId -> DivisionId)",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("ADMINISTRADOR"))],
)
def unassign_energetico_unidad(
    unidad_id: Annotated[int, Path(..., ge=1)],
    energetico_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    numero_cliente_id: Optional[int] = Query(
        None, ge=1, description="Opcional: si se usó un NumeroClienteId en la asignación"
    ),
    DivisionId: Optional[int] = Query(default=None, ge=1, description="Opcional: valida mismatch con UnidadId"),
):
    division_from_unidad = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    if DivisionId is not None and int(DivisionId) != int(division_from_unidad):
        _division_mismatch(int(unidad_id), int(DivisionId), int(division_from_unidad))

    _ = svc.unassign_from_division(
        db=db,
        division_id=division_from_unidad,
        energetico_id=energetico_id,
        numero_cliente_id=numero_cliente_id,
    )
    return None
