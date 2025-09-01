from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func, select
from fastapi import HTTPException

from app.db.models.unidad_medida import UnidadMedida
from app.schemas.unidad_medida import UnidadMedidaCreate, UnidadMedidaUpdate


class UnidadMedidaService:
    # Listado con búsqueda y paginación
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        query = db.query(UnidadMedida)

        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(UnidadMedida.Nombre).like(func.lower(like)))

        # total: usando subquery para que no afecten offset/limit
        total = db.scalar(select(func.count()).select_from(query.subquery()))

        items = (
            query.order_by(UnidadMedida.Nombre)
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {"total": total or 0, "data": items}

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

    def create(self, db: Session, payload: UnidadMedidaCreate) -> UnidadMedida:
        name = (payload.Nombre or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Nombre requerido")
        obj = UnidadMedida(Nombre=name)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, um_id: int, payload: UnidadMedidaUpdate) -> UnidadMedida:
        obj = self.get(db, um_id)
        name = (payload.Nombre or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Nombre requerido")
        obj.Nombre = name
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, um_id: int) -> None:
        obj = self.get(db, um_id)
        db.delete(obj)
        db.commit()
