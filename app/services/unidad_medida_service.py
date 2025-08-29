from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from app.db.models.unidad_medida import UnidadMedida

class UnidadMedidaService:
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        query = db.query(UnidadMedida)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(UnidadMedida.Nombre).like(func.lower(like)))
        total = query.count()
        items = (
            query.order_by(UnidadMedida.Nombre, UnidadMedida.Id)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def get(self, db: Session, id_: int) -> UnidadMedida:
        obj = db.query(UnidadMedida).filter(UnidadMedida.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
        return obj

    def create(self, db: Session, data, created_by: str | None = None) -> UnidadMedida:
        now = datetime.utcnow()
        obj = UnidadMedida(
            CreatedAt=now, UpdatedAt=now, Version=0, Active=True,
            CreatedBy=created_by, ModifiedBy=created_by,
            Nombre=data.Nombre, Sigla=data.Sigla,
        )
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def update(self, db: Session, id_: int, data, modified_by: str | None = None) -> UnidadMedida:
        obj = self.get(db, id_)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit(); db.refresh(obj)
        return obj

    def delete(self, db: Session, id_: int) -> None:
        obj = self.get(db, id_)
        db.delete(obj); db.commit()
