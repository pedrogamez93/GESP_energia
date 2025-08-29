from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from app.db.models.parametro_medicion import ParametroMedicion

class ParametroMedicionService:
    def list(self, db: Session, q: str | None) -> list[ParametroMedicion]:
        query = db.query(ParametroMedicion)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(ParametroMedicion.Nombre).like(func.lower(like)))
        return query.order_by(ParametroMedicion.Nombre).all()

    def get(self, db: Session, pm_id: int) -> ParametroMedicion:
        obj = db.query(ParametroMedicion).filter(ParametroMedicion.Id == pm_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Parámetro de medición no encontrado")
        return obj

    def create(self, db: Session, name: str) -> ParametroMedicion:
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Nombre requerido")
        obj = ParametroMedicion(Nombre=name.strip())
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def update(self, db: Session, pm_id: int, name: str) -> ParametroMedicion:
        obj = self.get(db, pm_id)
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Nombre requerido")
        obj.Nombre = name.strip()
        db.commit(); db.refresh(obj)
        return obj

    def delete(self, db: Session, pm_id: int) -> None:
        obj = self.get(db, pm_id)
        db.delete(obj); db.commit()
