# app/services/catalogo_simple_service.py
from __future__ import annotations
from typing import Type
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

# Se espera que los modelos tengan (Id, Nombre) y opcionalmente:
# CreatedAt, UpdatedAt, Version, Active, CreatedBy, ModifiedBy
class CatalogoSimpleService:
    def __init__(self, model: Type, has_audit: bool = False):
        self.model = model
        self.has_audit = has_audit

    # ---- Listado paginado ----
    def list(self, db: Session, q: str | None, page: int, page_size: int, include_inactive: bool = False) -> dict:
        M = self.model
        query = db.query(M)
        if self.has_audit and not include_inactive and hasattr(M, "Active"):
            query = query.filter(M.Active == True)

        if q:
            like = f"%{q}%"
            # coalesce para evitar NULLs
            query = query.filter(func.lower(func.coalesce(M.Nombre, "")).like(func.lower(like)))

        total = query.count()
        items = (
            query.order_by(M.Nombre.asc().nulls_last(), M.Id.asc())
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    # ---- Select liviano (Id, Nombre) ----
    def list_select(self, db: Session, q: str | None):
        M = self.model
        query = db.query(M.Id, M.Nombre)
        if self.has_audit and hasattr(M, "Active"):
            query = query.filter(M.Active == True)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(func.coalesce(M.Nombre, "")).like(func.lower(like)))
        return query.order_by(M.Nombre.asc().nulls_last(), M.Id.asc()).all()

    # ---- Get ----
    def get(self, db: Session, id: int):
        M = self.model
        obj = db.query(M).filter(M.Id == id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="No encontrado")
        return obj

    # ---- Create ----
    def create(self, db: Session, payload):
        M = self.model
        data = payload.model_dump(exclude_unset=True)
        if self.has_audit:
            now = datetime.utcnow()
            # set por defecto si existen estos campos
            for fld, val in [
                ("CreatedAt", now),
                ("UpdatedAt", now),
                ("Version", 1),
                ("Active", True),
            ]:
                if hasattr(M, fld):
                    data.setdefault(fld, val)
            for fld in ("CreatedBy", "ModifiedBy"):
                if hasattr(M, fld):
                    data.setdefault(fld, None)
        obj = M(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # ---- Update ----
    def update(self, db: Session, id: int, payload):
        M = self.model
        obj = self.get(db, id)
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(obj, k, v)
        if self.has_audit and hasattr(M, "UpdatedAt"):
            obj.UpdatedAt = datetime.utcnow()
        if self.has_audit and hasattr(M, "Version"):
            obj.Version = (obj.Version or 0) + 1
        db.commit()
        db.refresh(obj)
        return obj

    # ---- Delete (soft si has_audit) ----
    def delete(self, db: Session, id: int):
        M = self.model
        obj = self.get(db, id)
        if self.has_audit and hasattr(M, "Active"):
            if getattr(obj, "Active", True) is False:
                return  # ya inactivo
            obj.Active = False
            if hasattr(M, "UpdatedAt"):
                obj.UpdatedAt = datetime.utcnow()
            if hasattr(M, "Version"):
                obj.Version = (obj.Version or 0) + 1
            db.commit()
            return
        # hard delete si no hay auditoría
        db.delete(obj)
        db.commit()
