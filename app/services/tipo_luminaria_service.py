# app/services/tipo_luminaria_service.py
from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db.models.tipo_luminaria import TipoLuminaria

class TipoLuminariaService:
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        query = db.query(TipoLuminaria)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(TipoLuminaria.Nombre).like(func.lower(like)))
        total = query.count()
        items = (query.order_by(TipoLuminaria.Nombre, TipoLuminaria.Id)
                      .offset((page - 1) * page_size)
                      .limit(page_size)
                      .all())
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def list_select(self, db: Session, q: str | None):
        query = db.query(TipoLuminaria.Id, TipoLuminaria.Nombre)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(TipoLuminaria.Nombre).like(func.lower(like)))
        return query.order_by(TipoLuminaria.Nombre, TipoLuminaria.Id).all()

    def get(self, db: Session, id_: int) -> TipoLuminaria:
        obj = db.query(TipoLuminaria).filter(TipoLuminaria.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Tipo de luminaria no encontrado")
        return obj

    def create(self, db: Session, data):
        obj = TipoLuminaria(**data.model_dump())
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def update(self, db: Session, id_: int, data):
        obj = self.get(db, id_)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        db.commit(); db.refresh(obj)
        return obj

    def delete(self, db: Session, id_: int):
        obj = self.get(db, id_)
        db.delete(obj); db.commit()
