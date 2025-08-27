# app/services/tipo_equipo_calefaccion_service.py
from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_equipo_calefaccion_energetico import TipoEquipoCalefaccionEnergetico

class TipoEquipoCalefaccionService:
    # ----- Catálogo -----
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        query = db.query(TipoEquipoCalefaccion)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(TipoEquipoCalefaccion.Nombre).like(func.lower(like)))
        total = query.count()
        items = (query.order_by(TipoEquipoCalefaccion.Nombre, TipoEquipoCalefaccion.Id)
                      .offset((page - 1) * page_size)
                      .limit(page_size)
                      .all())
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def list_select(self, db: Session, q: str | None):
        query = db.query(TipoEquipoCalefaccion.Id, TipoEquipoCalefaccion.Nombre)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(TipoEquipoCalefaccion.Nombre).like(func.lower(like)))
        return query.order_by(TipoEquipoCalefaccion.Nombre, TipoEquipoCalefaccion.Id).all()

    def get(self, db: Session, id_: int) -> TipoEquipoCalefaccion:
        obj = db.query(TipoEquipoCalefaccion).filter(TipoEquipoCalefaccion.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Tipo de equipo de calefacción no encontrado")
        return obj

    def create(self, db: Session, data):
        obj = TipoEquipoCalefaccion(**data.model_dump())
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

    # ----- N:M con Energéticos -----
    def list_rel(self, db: Session, tipo_id: int):
        self.get(db, tipo_id)  # valida existencia
        rows = (db.query(TipoEquipoCalefaccionEnergetico)
                  .filter(TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId == tipo_id)
                  .order_by(TipoEquipoCalefaccionEnergetico.Id)
                  .all())
        return rows

    def add_rel(self, db: Session, tipo_id: int, energetico_id: int):
        self.get(db, tipo_id)
        obj = TipoEquipoCalefaccionEnergetico(
            TipoEquipoCalefaccionId=tipo_id,
            EnergeticoId=energetico_id
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
