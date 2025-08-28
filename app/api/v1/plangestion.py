from __future__ import annotations
from typing import Annotated, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Path, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.plangestion import (
    TareaDTO, TareaListDTO, TareaCreate, TareaUpdate, ResumenEstadoDTO
)
from app.services.plangestion_service import PlanGestionService
from app.schemas.auth import UserPublic
from app.core.security import require_roles

DbDep = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/api/v1/plangestion", tags=["Plan de Gestión"])

def _current_user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None) or request.headers.get("X-User-Id")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="userId no presente")
    return uid

# ---------- Listado de tareas ----------
@router.get("/tareas", response_model=List[TareaListDTO], summary="Lista paginada/filtrada de tareas")
def listar_tareas(
    response: Response,
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 10,
    active: Annotated[bool | None, Query()] = True,
    accion_id: Annotated[int | None, Query()] = None,
    dimension_brecha_id: Annotated[int | None, Query()] = None,
    fecha_desde: Annotated[datetime | None, Query()] = None,
    fecha_hasta: Annotated[datetime | None, Query()] = None,
    estado: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
):
    total, items = PlanGestionService(db).list_tareas(
        page=page,
        page_size=page_size,
        active=active,
        accion_id=accion_id,
        dimension_brecha_id=dimension_brecha_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        estado=estado,
        search=search,
    )
    total_pages = (total + page_size - 1) // page_size if page_size else 1
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Total-Pages"] = str(total_pages)
    return items

# Atajos legibles (compat con .NET): por acción / por dimensión
@router.get("/acciones/{accion_id}/tareas", response_model=List[TareaListDTO], summary="Tareas por acción")
def tareas_por_accion(
    accion_id: Annotated[int, Path(ge=1)],
    response: Response,
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 10,
):
    total, items = PlanGestionService(db).list_tareas(page=page, page_size=page_size, accion_id=accion_id)
    total_pages = (total + page_size - 1) // page_size if page_size else 1
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Total-Pages"] = str(total_pages)
    return items

@router.get("/dimension-brecha/{dimension_brecha_id}/tareas", response_model=List[TareaListDTO], summary="Tareas por dimensión de brecha")
def tareas_por_dimension(
    dimension_brecha_id: Annotated[int, Path(ge=1)],
    response: Response,
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 10,
):
    total, items = PlanGestionService(db).list_tareas(page=page, page_size=page_size, dimension_brecha_id=dimension_brecha_id)
    total_pages = (total + page_size - 1) // page_size if page_size else 1
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Total-Pages"] = str(total_pages)
    return items

# ---------- Resumen ----------
@router.get("/tareas/resumen/estado", response_model=List[ResumenEstadoDTO], summary="Resumen por EstadoAvance")
def resumen_estado(
    db: DbDep,
    active: Annotated[bool | None, Query()] = True,
    accion_id: Annotated[int | None, Query()] = None,
    dimension_brecha_id: Annotated[int | None, Query()] = None,
):
    return PlanGestionService(db).resumen_por_estado(active=active, accion_id=accion_id, dimension_brecha_id=dimension_brecha_id)

# ---------- Lectura ----------
@router.get("/tareas/{tarea_id}", response_model=TareaDTO, summary="Detalle de tarea")
def obtener_tarea(tarea_id: Annotated[int, Path(ge=1)], db: DbDep):
    t = PlanGestionService(db).get_tarea(tarea_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrada")
    return TareaDTO.model_validate(t)

# ---------- Escrituras (ADMIN) ----------
@router.post("/tareas", response_model=TareaDTO, status_code=status.HTTP_201_CREATED, summary="(ADMIN) Crear tarea")
def crear_tarea(
    data: TareaCreate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    created = PlanGestionService(db).create_tarea(data, created_by=current_user.id)
    return TareaDTO.model_validate(created)

@router.put("/tareas/{tarea_id}", response_model=TareaDTO, summary="(ADMIN) Actualizar tarea")
def actualizar_tarea(
    tarea_id: Annotated[int, Path(ge=1)],
    data: TareaUpdate,
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    updated = PlanGestionService(db).update_tarea(tarea_id, data, modified_by=current_user.id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrada")
    return TareaDTO.model_validate(updated)

@router.delete("/tareas/{tarea_id}", response_model=TareaDTO, summary="(ADMIN) Eliminar tarea (soft-delete)")
def eliminar_tarea(
    tarea_id: Annotated[int, Path(ge=1)],
    db: DbDep,
    current_user: Annotated[UserPublic, Depends(require_roles("ADMINISTRADOR"))],
):
    deleted = PlanGestionService(db).soft_delete_tarea(tarea_id, modified_by=current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrada")
    return TareaDTO.model_validate(deleted)

# ---------- Placeholders de .NET (actívalos si existen en tu API original) ----------
# @router.post("/accion", ...)               # crear acción
# @router.put("/objetivo/{id}", ...)         # actualizar objetivo
# @router.get("/reporte-consumo", ...)       # reportes agregados
# Lógi­ca pendiente de las consultas/órdenes originales (.NET/LINQ/SQL).
