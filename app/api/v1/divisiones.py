# app/api/v1/divisiones.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_roles
from app.schemas.auth import UserPublic
from app.schemas.division import DivisionDTO, DivisionListDTO, DivisionSelectDTO
from app.services.division_service import DivisionService

router = APIRouter(prefix="/api/v1/divisiones", tags=["Divisiones"])
svc = DivisionService()
DbDep = Annotated[Session, Depends(get_db)]

# ---- GET públicos ----
@router.get("", response_model=dict, summary="Listado paginado")
def list_divisiones(
    db: DbDep,
    q: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return svc.list(db, q, page, page_size)

@router.get("/select", response_model=List[DivisionSelectDTO], summary="(picker) Id/Nombre")
def select_divisiones(
    db: DbDep,
    q: str | None = Query(default=None),
    ServicioId: int | None = Query(default=None),
):
    rows = svc.list_select(db, q, ServicioId)
    return [DivisionSelectDTO(Id=r[0], Nombre=r[1]) for r in rows]

@router.get("/{division_id}", response_model=DivisionDTO, summary="Detalle")
def get_division(
    division_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    return svc.get(db, division_id)

@router.get("/servicio/{servicio_id}", response_model=List[DivisionListDTO], summary="Por servicio")
def get_divisiones_by_servicio(
    servicio_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    items = svc.by_servicio(db, servicio_id)
    return [DivisionListDTO.model_validate(x) for x in items]

@router.get("/edificio/{edificio_id}", response_model=List[DivisionListDTO], summary="Por edificio")
def get_divisiones_by_edificio(
    edificio_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    items = svc.by_edificio(db, edificio_id)
    return [DivisionListDTO.model_validate(x) for x in items]

@router.get("/region/{region_id}", response_model=List[DivisionListDTO], summary="Por región")
def get_divisiones_by_region(
    region_id: Annotated[int, Path(..., ge=1)],
    db: DbDep,
):
    items = svc.by_region(db, region_id)
    return [DivisionListDTO.model_validate(x) for x in items]

# ---- Por usuario (ADMIN) ----
@router.get("/usuario/{user_id}", response_model=List[DivisionListDTO],
            summary="Por usuario (vía UsuariosDivisiones)")
def get_divisiones_by_user(
    user_id: Annotated[str, Path(...)],
    _admin: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
    db: DbDep,
):
    items = svc.by_user(db, user_id)
    return [DivisionListDTO.model_validate(x) for x in items]
