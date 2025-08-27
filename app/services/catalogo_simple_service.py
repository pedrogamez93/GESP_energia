# app/services/catalogo_simple_service.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

# Este servicio es genérico; recibe el modelo SQLAlchemy
class CatalogoSimpleService:
    def __init__(self, model, has_audit: bool = False):
        self.model = model
        self.has_audit = has_audit

    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        M = self.model
        query = db.query(M)
        if hasattr(M, "Nombre") and q:
            like = f"%{q}%"
            query = query.filter(func.lower(M.Nombre).like(func.lower(like)))
        total = query.count()
        items = (query.order_by(M.Nombre if hasattr(M, "Nombre") else M.Id, M.Id)
                      .offset((page - 1) * page_size)
                      .limit(page_size)
                      .all())
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def list_select(self, db: Session, q: str | None):
        M = self.model
        if hasattr(M, "Nombre"):
            query = db.query(M.Id, M.Nombre)
            if q:
                like = f"%{q}%"
                query = query.filter(func.lower(M.Nombre).like(func.lower(like)))
            return query.order_by(M.Nombre, M.Id).all()
        else:
            return db.query(M.Id).order_by(M.Id).all()

    def get(self, db: Session, id_: int):
        M = self.model
        obj = db.query(M).filter(M.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        return obj

    def create(self, db: Session, data):
        M = self.model
        payload = data.model_dump(exclude_unset=True)
        if self.has_audit:
            now = datetime.utcnow()
            payload.setdefault("CreatedAt", now)
            payload.setdefault("UpdatedAt", now)
            payload.setdefault("Version", 0)
            payload.setdefault("Active", True)
        obj = M(**payload)
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def update(self, db: Session, id_: int, data):
        M = self.model
        obj = self.get(db, id_)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        if self.has_audit and hasattr(obj, "UpdatedAt"):
            obj.UpdatedAt = datetime.utcnow()
        db.commit(); db.refresh(obj)
        return obj

    def delete(self, db: Session, id_: int):
        M = self.model
        obj = self.get(db, id_)
        db.delete(obj); db.commit()
