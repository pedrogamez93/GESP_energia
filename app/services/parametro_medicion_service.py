from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models.parametro_medicion import ParametroMedicion
from fastapi import HTTPException

class ParametroMedicionService:
    # Solo lectura para no chocar con restricciones desconocidas de la BD
    def list(self, db: Session, q: str | None):
        query = db.query(ParametroMedicion)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(ParametroMedicion.Nombre).like(func.lower(like)))
        return query.order_by(ParametroMedicion.Nombre).all()

    def get(self, db: Session, id_: int):
        obj = db.query(ParametroMedicion).filter(ParametroMedicion.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Parámetro de medición no encontrado")
        return obj
