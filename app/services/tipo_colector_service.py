# app/services/tipo_colector_service.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db.models.tipo_colector import TipoColector

def _now():
    return datetime.utcnow()

class TipoColectorService:
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        page = max(1, int(page or 1)); size = max(1, min(200, int(page_size or 50)))
        query = db.query(TipoColector)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(TipoColector.Nombre).like(func.lower(like)))
        total = query.count()
        items = (query.order_by(TipoColector.Nombre, TipoColector.Id)
                      .offset((page - 1) * size)
                      .limit(size)
                      .all())
        return {"total": total, "page": page, "page_size": size, "items": items}

    def get(self, db: Session, id_: int) -> TipoColector:
        obj = db.query(TipoColector).filter(TipoColector.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Tipo de colector no encontrado")
        return obj

    def create(self, db: Session, data, user: str | None = None):
        now = _now()
        obj = TipoColector(
            Nombre=(getattr(data, "Nombre", None) or "").strip(),
            CreatedAt=now, UpdatedAt=now, Version=1, Active=True,
            CreatedBy=user, ModifiedBy=user
        )
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def update(self, db: Session, id_: int, data, user: str | None = None):
        obj = self.get(db, id_)
        if hasattr(data, "Nombre"):
            obj.Nombre = (data.Nombre or "").strip()
        if hasattr(data, "Active") and data.Active is not None:
            obj.Active = bool(data.Active)
        obj.UpdatedAt = _now()
        obj.Version = (obj.Version or 0) + 1
        if user:
            obj.ModifiedBy = user
        db.commit(); db.refresh(obj)
        return obj

    def delete(self, db: Session, id_: int):
        obj = self.get(db, id_)
        db.delete(obj); db.commit()
