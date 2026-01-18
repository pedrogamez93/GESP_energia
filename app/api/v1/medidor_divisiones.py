from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.medidor_division import MedidorDivisionDTO, IdsPayload
from app.services.medidor_division_service import MedidorDivisionService

# ✅ Alias UnidadId -> DivisionId (UnidadesInmuebles.InmuebleId)
from app.services.unidad_scope import division_id_from_unidad

router = APIRouter(prefix="/api/v1/medidor-divisiones", tags=["MedidorDivision"])
svc = MedidorDivisionService()
DbDep = Annotated[Session, Depends(get_db)]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_division_from_unidad_or_raise(db: Session, unidad_id: int) -> int:
    """
    Resuelve UnidadId -> DivisionId vía UnidadesInmuebles.InmuebleId.
    """
    try:
        div = division_id_from_unidad(db, int(unidad_id))
        return int(div)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=404,
            detail={"code": "unidad_not_found", "msg": "UnidadId no encontrada"},
        )


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


# ─────────────────────────────────────────────────────────────────────────────
# GET: listado por división
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/division/{division_id}",
    response_model=List[MedidorDivisionDTO],
    summary="Medidores asociados a una división",
)
def list_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.list_by_division(db, division_id)


# ─────────────────────────────────────────────────────────────────────────────
# ✅ GET: listado por unidad (ALIAS)
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/unidad/{unidad_id}",
    response_model=List[MedidorDivisionDTO],
    summary="Medidores asociados a una unidad (alias: UnidadId -> DivisionId)",
)
def list_por_unidad(
    unidad_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    division_id = _resolve_division_from_unidad_or_raise(db, int(unidad_id))
    return svc.list_by_division(db, division_id)


# ─────────────────────────────────────────────────────────────────────────────
# GET: divisiones asociadas a un medidor
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/medidor/{medidor_id}/divisiones",
    response_model=List[int],
    summary="Divisiones asociadas a un medidor",
)
def list_divisiones_por_medidor(
    medidor_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.list_divisiones_by_medidor(db, medidor_id)


# ─────────────────────────────────────────────────────────────────────────────
# PUT: reemplazar set de medidores para una división
# ─────────────────────────────────────────────────────────────────────────────
@router.put(
    "/division/{division_id}",
    response_model=List[MedidorDivisionDTO],
    summary="(ADMINISTRADOR) Reemplaza set de medidores para una división",
)
def replace_set(
    division_id: Annotated[int, Path(..., ge=1)],
    payload: IdsPayload,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.replace_for_division(db, division_id, payload.Ids or [])


# ─────────────────────────────────────────────────────────────────────────────
# ✅ PUT: reemplazar set de medidores para una UNIDAD (ALIAS)
# ─────────────────────────────────────────────────────────────────────────────
@router.put(
    "/unidad/{unidad_id}",
    response_model=List[MedidorDivisionDTO],
    summary="(ADMINISTRADOR) Reemplaza set de medidores para una unidad (alias UnidadId -> DivisionId)",
)
def replace_set_por_unidad(
    unidad_id: Annotated[int, Path(..., ge=1)],
    payload: IdsPayload,
    db: DbDep,
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
    DivisionId: Optional[int] = Query(default=None, ge=1, description="Opcional: valida mismatch con UnidadId"),
):
    division_from_unidad = _resolve_division_from_unidad_or_raise(db, int(unidad_id))

    if DivisionId is not None and int(DivisionId) != int(division_from_unidad):
        _division_mismatch(int(unidad_id), int(DivisionId), int(division_from_unidad))

    return svc.replace_for_division(db, division_from_unidad, payload.Ids or [])
