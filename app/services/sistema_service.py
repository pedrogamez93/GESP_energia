from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from fastapi import HTTPException

from app.db.models.sistema import Sistema


class SistemaService:
    def _order_by_nombre_nulls_last(self):
        # CASE WHEN Nombre IS NULL THEN 1 ELSE 0 END, Nombre ASC, Id ASC
        return (
            case((Sistema.Nombre.is_(None), 1), else_=0),
            func.lower(Sistema.Nombre).asc(),
            Sistema.Id.asc(),
        )

    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        query = db.query(Sistema).filter(Sistema.Active.is_(True))
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(Sistema.Nombre).like(func.lower(like)))

        total = query.count()
        items = (
            query.order_by(*self._order_by_nombre_nulls_last())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def list_select(self, db: Session, q: str | None):
        query = db.query(Sistema.Id, Sistema.Nombre).filter(Sistema.Active.is_(True))
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(Sistema.Nombre).like(func.lower(like)))
        return query.order_by(*self._order_by_nombre_nulls_last()).all()

    def get(self, db: Session, id_: int) -> Sistema:
        obj = db.query(Sistema).filter(Sistema.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Sistema no encontrado")
        return obj

    def create(self, db: Session, data, user: str | None = None):
        now = datetime.utcnow()
        obj = Sistema(
            Nombre=data.Nombre,
            CreatedAt=now,
            UpdatedAt=now,
            Version=1,
            Active=True,
            CreatedBy=user,
            ModifiedBy=user,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, id_: int, data, user: str | None = None):
        obj = self.get(db, id_)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.UpdatedAt = datetime.utcnow()
        obj.Version = (obj.Version or 0) + 1
        if user:
            obj.ModifiedBy = user
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id_: int, user: str | None = None):
        # soft-delete
        obj = self.get(db, id_)
        if not obj.Active:
            return
        obj.Active = False
        obj.UpdatedAt = datetime.utcnow()
        obj.Version = (obj.Version or 0) + 1
        if user:
            obj.ModifiedBy = user
        db.commit()
