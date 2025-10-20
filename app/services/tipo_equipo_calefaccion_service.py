# app/services/tipo_equipo_calefaccion_service.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_equipo_calefaccion_energetico import TipoEquipoCalefaccionEnergetico

def _now():
    return datetime.utcnow()

class TipoEquipoCalefaccionService:
    # ----- Catálogo -----
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        page = max(1, int(page or 1)); size = max(1, min(200, int(page_size or 50)))
        query = db.query(TipoEquipoCalefaccion)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(TipoEquipoCalefaccion.Nombre).like(func.lower(like)))
        total = query.count()
        items = (query.order_by(TipoEquipoCalefaccion.Nombre, TipoEquipoCalefaccion.Id)
                      .offset((page - 1) * size)
                      .limit(size)
                      .all())
        return {"total": total, "page": page, "page_size": size, "items": items}

    def get(self, db: Session, id_: int) -> TipoEquipoCalefaccion:
        obj = db.query(TipoEquipoCalefaccion).filter(TipoEquipoCalefaccion.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Tipo de equipo de calefacción no encontrado")
        return obj

    def create(self, db: Session, data, user: str | None = None):
        now = _now()
        obj = TipoEquipoCalefaccion(
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

    # ----- N:M con Energéticos (mantenedor de compatibilidades) -----
    def list_rel(self, db: Session, tipo_id: int):
        self.get(db, tipo_id)  # valida existencia
        return (db.query(TipoEquipoCalefaccionEnergetico)
                  .filter(TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId == tipo_id)
                  .order_by(TipoEquipoCalefaccionEnergetico.Id)
                  .all())

    def add_rel(self, db: Session, tipo_id: int, energetico_id: int):
        self.get(db, tipo_id)
        exists = (db.query(TipoEquipoCalefaccionEnergetico)
                    .filter(TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId == tipo_id,
                            TipoEquipoCalefaccionEnergetico.EnergeticoId == energetico_id)
                    .first())
        if exists:
            return exists
        obj = TipoEquipoCalefaccionEnergetico(
            TipoEquipoCalefaccionId=tipo_id, EnergeticoId=energetico_id
        )
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def delete_rel(self, db: Session, rel_id: int):
        obj = db.query(TipoEquipoCalefaccionEnergetico).filter(
            TipoEquipoCalefaccionEnergetico.Id == rel_id
        ).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Relación no encontrada")
        db.delete(obj); db.commit()
