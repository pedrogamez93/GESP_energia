from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from app.db.models.unidad_medida import UnidadMedida

class UnidadMedidaService:
    def list(self, db: Session, q: str | None) -> list[UnidadMedida]:
        query = db.query(UnidadMedida)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(UnidadMedida.Nombre).like(func.lower(like)))
        return query.order_by(UnidadMedida.Nombre).all()

    def list_select(self, db: Session, q: str | None = None) -> list[tuple[int, str | None]]:
        query = db.query(UnidadMedida.Id, UnidadMedida.Nombre)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(UnidadMedida.Nombre).like(func.lower(like)))
        return query.order_by(UnidadMedida.Nombre).all()

    def get(self, db: Session, um_id: int) -> UnidadMedida:
        obj = db.query(UnidadMedida).filter(UnidadMedida.Id == um_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
        return obj

    def create(self, db: Session, name: str) -> UnidadMedida:
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Nombre requerido")
        obj = UnidadMedida(Nombre=name.strip())
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def update(self, db: Session, um_id: int, name: str) -> UnidadMedida:
        obj = self.get(db, um_id)
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Nombre requerido")
        obj.Nombre = name.strip()
        db.commit(); db.refresh(obj)
        return obj

    def delete(self, db: Session, um_id: int) -> None:
        obj = self.get(db, um_id)
        db.delete(obj); db.commit()
