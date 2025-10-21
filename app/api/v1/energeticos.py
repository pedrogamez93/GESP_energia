from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Path, status, HTTPException, Response
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic

from app.schemas.energetico import (
    EnergeticoDTO,
    EnergeticoListDTO,
    EnergeticoCreate,
    EnergeticoUpdate,
    EnergeticoSelectDTO,
    EnergeticoUMDTO,
    EnergeticoUMCreate,
    EnergeticoUMUpdate,
    EnergeticoDivisionDTO,
    EnergeticoPage,  # wrapper de paginación
)
from app.services.energetico_service import EnergeticoService

router = APIRouter(prefix="/api/v1/energeticos", tags=["Energeticos"])
DbDep = Annotated[Session, Depends(get_db)]
svc = EnergeticoService()


# =============================
#         LECTURAS
# =============================

@router.get(
    "",
    response_model=EnergeticoPage,
    summary="Listar energéticos (paginado)"
)
def list_energeticos(
    db: DbDep,
    q: str | None = Query(default=None, description="Filtro por nombre (contiene)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = q.strip() if isinstance(q, str) else q
    res = svc.list(db, q, page, page_size)  # {"total": X, "data": [Energetico]}
    items = [EnergeticoListDTO.model_validate(it) for it in (res.get("data") or [])]
    return EnergeticoPage(total=int(res.get("total") or 0), data=items)


@router.get(
    "/select",
    response_model=list[EnergeticoSelectDTO],
    summary="Listado liviano (Id, Nombre)"
)
def list_energeticos_select(db: DbDep):
    rows = svc.list_select(db) or []  # List[Tuple[Id, Nombre]]
    return [EnergeticoSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]


@router.get(
    "/{id}",
    response_model=EnergeticoDTO,
    summary="Obtener energético por Id"
)
def get_energetico(
    db: DbDep,
    id: Annotated[int, Path(..., ge=1)],
):
    obj = svc.get(db, id)
    return EnergeticoDTO.model_validate(obj)


@router.get(
    "/division/{division_id}",
    response_model=list[EnergeticoDivisionDTO],
    summary="Energéticos declarados por división"
)
def get_by_division(
    db: DbDep,
    division_id: Annotated[int, Path(..., ge=1)],
):
    rows = svc.by_division(db, division_id)
    return [EnergeticoDivisionDTO.model_validate(x) for x in rows]


@router.get(
    "/activos/division/{division_id}",
    response_model=list[EnergeticoDTO],
    summary="Energéticos activos por división"
)
def get_activos_by_division(
    db: DbDep,
    division_id: Annotated[int, Path(..., ge=1)],
):
    rows = svc.activos_by_division(db, division_id)
    return [EnergeticoDTO.model_validate(x) for x in rows]


@router.get(
    "/edificio/{edificio_id}",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="(Pendiente) Energéticos por edificio"
)
def get_by_edificio(
    db: DbDep,
    edificio_id: Annotated[int, Path(..., ge=1)],
):
    # Requiere definir relación a Edificio para implementarlo
    raise HTTPException(status_code=501, detail="Pendiente implementar (requiere modelo/relación con Edificio)")


# =============================
#       ESCRITURAS (ADMIN)
# =============================

@router.post(
    "",
    response_model=EnergeticoDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMINISTRADOR) Crear energético"
)
def create_energetico(
    payload: EnergeticoCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.create(db, payload)
    return EnergeticoDTO.model_validate(obj)


@router.put(
    "/{id}",
    response_model=EnergeticoDTO,
    summary="(ADMINISTRADOR) Actualizar energético"
)
def update_energetico(
    id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    obj = svc.update(db, id, payload)
    return EnergeticoDTO.model_validate(obj)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMINISTRADOR) Eliminar energético (hard delete)"
)
def delete_energetico(
    id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================
#  UNIDADES DE MEDIDA por ENE
#      (N:M con metadata)
#  Se mantienen ALIAS para
#  compatibilidad:
#   - /{id}/unidades-medida
#   - /{id}/unidades
#   - /um/{um_id}
#   - /unidades/{um_id}
# =============================

# ---- LISTAR UM DE UN ENERGÉTICO ----
@router.get(
    "/{energetico_id}/unidades-medida",
    response_model=list[EnergeticoUMDTO],
    summary="Listar unidades de medida por energético"
)
@router.get(  # alias compatible
    "/{energetico_id}/unidades",
    response_model=list[EnergeticoUMDTO],
    include_in_schema=False
)
def list_um(
    energetico_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    rows = svc.list_um(db, energetico_id)
    return [EnergeticoUMDTO.model_validate(x) for x in rows]


# ---- AGREGAR UM A UN ENERGÉTICO ----
@router.post(
    "/{energetico_id}/unidades-medida",
    response_model=EnergeticoUMDTO,
    status_code=status.HTTP_201_CREATED,
    summary="(ADMINISTRADOR) Agregar UM a un energético"
)
@router.post(  # alias compatible
    "/{energetico_id}/unidades",
    response_model=EnergeticoUMDTO,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False
)
def add_um(
    energetico_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoUMCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    row = svc.add_um(db, energetico_id, payload)
    return EnergeticoUMDTO.model_validate(row)


# ---- ACTUALIZAR RELACIÓN UM ----
@router.put(
    "/um/{um_id}",
    response_model=EnergeticoUMDTO,
    summary="(ADMINISTRADOR) Actualizar relación UM de un energético"
)
@router.put(  # alias compatible
    "/unidades/{um_id}",
    response_model=EnergeticoUMDTO,
    include_in_schema=False
)
def update_um(
    um_id: Annotated[int, Path(..., ge=1)],
    payload: EnergeticoUMUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    row = svc.update_um(db, um_id, payload)
    return EnergeticoUMDTO.model_validate(row)


# ---- ELIMINAR RELACIÓN UM ----
@router.delete(
    "/um/{um_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="(ADMINISTRADOR) Eliminar relación UM de un energético"
)
@router.delete(  # alias compatible
    "/unidades/{um_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False
)
def delete_um(
    um_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete_um(db, um_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
