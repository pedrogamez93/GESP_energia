# app/services/edificio_service.py
from __future__ import annotations
from typing import List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from fastapi import HTTPException

from app.db.models.edificio import Edificio

def _display_nombre(e: Edificio) -> str:
    # etiqueta amigable para selects: priorizamos Calle/Numero; si no, Direccion
    base = (e.Calle or e.Direccion or "").strip()
    num  = (e.Numero or "").strip()
    if base and num:
        return f"{base} {num}"
    return base or num or f"Edificio #{e.Id}"

class EdificioService:
    def list(self, db: Session, q: str | None, page: int, page_size: int,
             ComunaId: int | None = None) -> dict:
        query = db.query(Edificio)
        if q:
            like = f"%{q}%"
            query = query.filter(
                func.lower(func.coalesce(Edificio.Calle, "")).like(func.lower(like)) |
                func.lower(func.coalesce(Edificio.Direccion, "")).like(func.lower(like)) |
                func.lower(func.coalesce(Edificio.Numero, "")).like(func.lower(like))
            )
        if ComunaId is not None:
            query = query.filter(Edificio.ComunaId == ComunaId)

        total = query.count()
        items = (
            query.order_by(Edificio.Calle, Edificio.Numero, Edificio.Id)
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def list_select(self, db: Session, q: str | None, ComunaId: int | None = None) -> List[tuple[int, str]]:
        query = db.query(Edificio)
        if ComunaId is not None:
            query = query.filter(Edificio.ComunaId == ComunaId)
        if q:
            like = f"%{q}%"
            query = query.filter(
                func.lower(func.coalesce(Edificio.Calle, "")).like(func.lower(like)) |
                func.lower(func.coalesce(Edificio.Direccion, "")).like(func.lower(like))
            )
        rows = query.order_by(Edificio.Calle, Edificio.Numero, Edificio.Id).all()
        return [(e.Id, _display_nombre(e)) for e in rows]

    def get(self, db: Session, edificio_id: int) -> Edificio:
        obj = db.query(Edificio).filter(Edificio.Id == edificio_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Edificio no encontrado")
        return obj

    # --- ADMIN ---
    def create(self, db: Session, data: dict, created_by: str | None) -> Edificio:
        now = datetime.utcnow()
        obj = Edificio(
            CreatedAt=now, UpdatedAt=now,
            Version=1, Active=True,
            CreatedBy=created_by,
            **data
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, edificio_id: int, data: dict, modified_by: str | None) -> Edificio:
        obj = self.get(db, edificio_id)
        for k, v in (data or {}).items():
            setattr(obj, k, v)
        obj.ModifiedBy = modified_by
        obj.UpdatedAt = datetime.utcnow()
        obj.Version = (obj.Version or 0) + 1
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, edificio_id: int) -> None:
        obj = self.get(db, edificio_id)
        db.delete(obj)
        db.commit()
