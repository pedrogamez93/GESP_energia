from typing import Annotated, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.catalogos_equipo import SelectDTO
from app.services.catalogos_equipo_service import CatalogosEquipoService

router = APIRouter(prefix="/api/v1/catalogos-equipos", tags=["Catálogos • Equipos"])
svc = CatalogosEquipoService()
DbDep = Annotated[Session, Depends(get_db)]

@router.get("/sistemas", response_model=List[SelectDTO])
def select_sistemas(db: DbDep, q: str | None = Query(default=None)):
    rows = svc.list_sistemas(db, q)
    return [SelectDTO(Id=r[0], Nombre=r[1]) for r in rows]

@router.get("/modos-operacion", response_model=List[SelectDTO])
def select_modos(db: DbDep, q: str | None = Query(default=None)):
    rows = svc.list_modos(db, q)
    return [SelectDTO(Id=r[0], Nombre=r[1]) for r in rows]

@router.get("/tipos-tecnologia", response_model=List[SelectDTO])
def select_tipos_tecnologia(db: DbDep, q: str | None = Query(default=None)):
    rows = svc.list_tipos_tecnologia(db, q)
    return [SelectDTO(Id=r[0], Nombre=r[1]) for r in rows]
