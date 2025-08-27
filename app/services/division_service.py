# app/services/division_service.py
from __future__ import annotations
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func

from fastapi import HTTPException
from app.db.models.division import Division
from app.db.models.usuarios_divisiones import UsuarioDivision

class DivisionService:
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        query = db.query(Division)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(Division.Nombre).like(func.lower(like)))
        total = query.count()
        items = (
            query.order_by(Division.Nombre)
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def get(self, db: Session, division_id: int) -> Division:
        obj = db.query(Division).filter(Division.Id == division_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="División no encontrada")
        return obj

    def by_user(self, db: Session, user_id: str) -> List[Division]:
        ids = (
            db.query(UsuarioDivision.DivisionId)
              .filter(UsuarioDivision.UsuarioId == user_id)
              .all()
        )
        id_list = [r[0] for r in ids]
        if not id_list:
            return []
        return (
            db.query(Division)
              .filter(Division.Id.in_(id_list))
              .order_by(Division.Nombre)
              .all()
        )

    def by_servicio(self, db: Session, servicio_id: int) -> List[Division]:
        return (
            db.query(Division)
              .filter(Division.ServicioId == servicio_id)
              .order_by(Division.Nombre)
              .all()
        )

    def by_edificio(self, db: Session, edificio_id: int) -> List[Division]:
        return (
            db.query(Division)
              .filter(Division.EdificioId == edificio_id)
              .order_by(Division.Nombre)
              .all()
        )

    def by_region(self, db: Session, region_id: int) -> List[Division]:
        return (
            db.query(Division)
              .filter(Division.RegionId == region_id)
              .order_by(Division.Nombre)
              .all()
        )

    def list_select(self, db: Session, q: str | None, servicio_id: int | None) -> List[tuple[int, str | None]]:
        query = db.query(Division.Id, Division.Nombre)
        if servicio_id is not None:
            query = query.filter(Division.ServicioId == servicio_id)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(Division.Nombre).like(func.lower(like)))
        return query.order_by(Division.Nombre).all()
