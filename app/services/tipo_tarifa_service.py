from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from app.db.models.tipo_tarifa import TipoTarifa

class TipoTarifaService:
    def list(self, db: Session, q: str | None) -> list[TipoTarifa]:
        query = db.query(TipoTarifa)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(TipoTarifa.Nombre).like(func.lower(like)))
        return query.order_by(TipoTarifa.Nombre).all()

    def get(self, db: Session, tipo_tarifa_id: int) -> TipoTarifa:
        obj = db.query(TipoTarifa).filter(TipoTarifa.Id == tipo_tarifa_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Tipo de tarifa no encontrado")
        return obj

    def create(self, db: Session, name: str) -> TipoTarifa:
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Nombre requerido")
        obj = TipoTarifa(Nombre=name.strip())
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def update(self, db: Session, tipo_tarifa_id: int, name: str) -> TipoTarifa:
        obj = self.get(db, tipo_tarifa_id)
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Nombre requerido")
        obj.Nombre = name.strip()
        db.commit(); db.refresh(obj)
        return obj

    def delete(self, db: Session, tipo_tarifa_id: int) -> None:
        obj = self.get(db, tipo_tarifa_id)
        db.delete(obj); db.commit()
