from __future__ import annotations
from datetime import datetime
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.db.models.plangestion_tarea import PlanGestionTarea
from app.schemas.plangestion import (
    TareaDTO, TareaListDTO, TareaCreate, TareaUpdate, ResumenEstadoDTO
)

class PlanGestionService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- Listado con filtros y paginación ----------
    def list_tareas(
        self,
        page: int = 1,
        page_size: int = 10,
        active: Optional[bool] = True,
        accion_id: Optional[int] = None,
        dimension_brecha_id: Optional[int] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        estado: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[int, list[TareaListDTO]]:
        q = self.db.query(PlanGestionTarea)

        if active is not None:
            q = q.filter(PlanGestionTarea.Active == active)
        if accion_id is not None:
            q = q.filter(PlanGestionTarea.AccionId == accion_id)
        if dimension_brecha_id is not None:
            q = q.filter(PlanGestionTarea.DimensionBrechaId == dimension_brecha_id)
        if fecha_desde is not None:
            q = q.filter(PlanGestionTarea.FechaInicio >= fecha_desde)
        if fecha_hasta is not None:
            q = q.filter(PlanGestionTarea.FechaFin <= fecha_hasta)
        if estado:
            q = q.filter(PlanGestionTarea.EstadoAvance == estado)
        if search:
            like = f"%{search}%"
            q = q.filter(or_(
                PlanGestionTarea.Nombre.like(like),
                PlanGestionTarea.Responsable.like(like),
                PlanGestionTarea.Observaciones.like(like),
            ))

        total = q.with_entities(func.count(PlanGestionTarea.Id)).scalar() or 0

        size = max(1, min(200, page_size))
        items = (
            q.order_by(PlanGestionTarea.FechaFin.desc(), PlanGestionTarea.Id.desc())
             .offset((page - 1) * size)
             .limit(size)
             .all()
        )
        return total, [TareaListDTO.model_validate(x) for x in items]

    # ---------- Resumen ----------
    def resumen_por_estado(
        self,
        active: Optional[bool] = True,
        accion_id: Optional[int] = None,
        dimension_brecha_id: Optional[int] = None,
    ) -> list[ResumenEstadoDTO]:
        q = self.db.query(PlanGestionTarea.EstadoAvance, func.count().label("Cantidad"))
        if active is not None:
            q = q.filter(PlanGestionTarea.Active == active)
        if accion_id is not None:
            q = q.filter(PlanGestionTarea.AccionId == accion_id)
        if dimension_brecha_id is not None:
            q = q.filter(PlanGestionTarea.DimensionBrechaId == dimension_brecha_id)
        q = q.group_by(PlanGestionTarea.EstadoAvance).order_by(func.count().desc())
        rows = q.all()
        return [ResumenEstadoDTO(EstadoAvance=r[0], Cantidad=r[1]) for r in rows]

    # ---------- CRUD ----------
    def get_tarea(self, tarea_id: int) -> PlanGestionTarea | None:
        return self.db.query(PlanGestionTarea).filter(PlanGestionTarea.Id == tarea_id).first()

    def create_tarea(self, data: TareaCreate, created_by: str) -> PlanGestionTarea:
        now = datetime.utcnow()
        t = PlanGestionTarea(
            CreatedAt=now,
            UpdatedAt=now,
            Version=1,
            Active=True,
            CreatedBy=created_by,
            ModifiedBy=created_by,
            **data.model_dump(exclude_unset=True),
        )
        self.db.add(t)
        self.db.commit()
        self.db.refresh(t)
        return t

    def update_tarea(self, tarea_id: int, data: TareaUpdate, modified_by: str) -> PlanGestionTarea | None:
        t = self.get_tarea(tarea_id)
        if not t:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(t, k, v)
        t.UpdatedAt = datetime.utcnow()
        t.ModifiedBy = modified_by
        t.Version = (t.Version or 0) + 1
        self.db.commit()
        self.db.refresh(t)
        return t

    def soft_delete_tarea(self, tarea_id: int, modified_by: str) -> PlanGestionTarea | None:
        t = self.get_tarea(tarea_id)
        if not t:
            return None
        if not t.Active:
            return t
        t.Active = False
        t.UpdatedAt = datetime.utcnow()
        t.ModifiedBy = modified_by
        t.Version = (t.Version or 0) + 1
        self.db.commit()
        self.db.refresh(t)
        return t
