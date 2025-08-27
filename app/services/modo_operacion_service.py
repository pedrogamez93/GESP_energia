# app/services/modo_operacion_service.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db.models.modo_operacion import ModoOperacion

class ModoOperacionService:
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        query = db.query(ModoOperacion)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(ModoOperacion.Nombre).like(func.lower(like)))
        total = query.count()
        items = (query.order_by(ModoOperacion.Nombre, ModoOperacion.Id)
                      .offset((page - 1) * page_size)
                      .limit(page_size)
                      .all())
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def list_select(self, db: Session, q: str | None):
        query = db.query(ModoOperacion.Id, ModoOperacion.Nombre)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(ModoOperacion.Nombre).like(func.lower(like)))
        return query.order_by(ModoOperacion.Nombre, ModoOperacion.Id).all()

    def get(self, db: Session, id_: int) -> ModoOperacion:
        obj = db.query(ModoOperacion).filter(ModoOperacion.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Modo de operación no encontrado")
        return obj

    def create(self, db: Session, data):
        now = datetime.utcnow()
        obj = ModoOperacion(
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
