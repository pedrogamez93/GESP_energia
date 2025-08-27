from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.equipo import EquipoDTO, EquipoListDTO, EquipoCreate, EquipoUpdate
from app.services.equipo_service import EquipoService

router = APIRouter(prefix="/api/v1/equipos", tags=["Equipos"])
svc = EquipoService()
DbDep = Annotated[Session, Depends(get_db)]

# ---- GET públicos ----
@router.get("", response_model=dict, summary="Listado paginado de equipos")
def list_equipos(
    db: DbDep,
    q: str | None = Query(default=None, description="Busca en Marca/Modelo"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    DivisionId: int | None = Query(default=None),
    EnergeticoId: int | None = Query(default=None),
    Direction: Literal["in", "out"] | None = Query(default=None, pattern="^(in|out)$"),
):
    return svc.list(db, q, page, page_size, DivisionId, EnergeticoId, Direction)

@router.get("/{equipo_id}", response_model=EquipoDTO, summary="Detalle de equipo")
def get_equipo(
    equipo_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.get(db, equipo_id)

@router.get("/division/{division_id}", response_model=list[EquipoListDTO], summary="Equipos por división")
def list_por_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    data = svc.list(db, q=None, page=1, page_size=10_000, division_id=division_id)
    return [EquipoListDTO.model_validate(x) for x in data["items"]]

# ---- Escrituras (ADMINISTRADOR) ----
@router.post("", response_model=EquipoDTO, status_code=status.HTTP_201_CREATED,
             summary="(ADMINISTRADOR) Crear equipo")
def create_equipo(
    payload: EquipoCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.create(db, payload, created_by=current_user.id)

@router.put("/{equipo_id}", response_model=EquipoDTO,
            summary="(ADMINISTRADOR) Actualizar equipo")
def update_equipo(
    equipo_id: int,
    payload: EquipoUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    return svc.update(db, equipo_id, payload, modified_by=current_user.id)

@router.delete("/{equipo_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="(ADMINISTRADOR) Eliminar equipo (hard delete)")
def delete_equipo(
    equipo_id: int,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    svc.delete(db, equipo_id)
    return None
