# app/services/sistema_service.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db.models.sistema import Sistema

class SistemaService:
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        query = db.query(Sistema)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(Sistema.Nombre).like(func.lower(like)))
        total = query.count()
        items = (query.order_by(Sistema.Nombre, Sistema.Id)
                      .offset((page - 1) * page_size)
                      .limit(page_size)
                      .all())
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def list_select(self, db: Session, q: str | None):
        query = db.query(Sistema.Id, Sistema.Nombre)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(Sistema.Nombre).like(func.lower(like)))
        return query.order_by(Sistema.Nombre, Sistema.Id).all()

    def get(self, db: Session, id_: int) -> Sistema:
        obj = db.query(Sistema).filter(Sistema.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Sistema no encontrado")
        return obj

    def create(self, db: Session, data):
        now = datetime.utcnow()
        obj = Sistema(
            Nombre=data.Nombre,
            CreatedAt=now, UpdatedAt=now,
            Version=0, Active=True
        )
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def update(self, db: Session, id_: int, data):
        obj = self.get(db, id_)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.UpdatedAt = datetime.utcnow()
        db.commit(); db.refresh(obj)
        return obj

    def delete(self, db: Session, id_: int):
        obj = self.get(db, id_)
        db.delete(obj); db.commit()
