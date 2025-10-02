# app/services/unidad_medida_service.py
from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func, select, or_
from fastapi import HTTPException

from app.db.models.unidad_medida import UnidadMedida
from app.schemas.unidad_medida import UnidadMedidaCreate, UnidadMedidaUpdate

class UnidadMedidaService:
    # Listado con búsqueda y paginación
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        query = db.query(UnidadMedida)

        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    func.lower(UnidadMedida.Nombre).like(func.lower(like)),
                    func.lower(UnidadMedida.Abrv).like(func.lower(like)),  # <-- buscar también por Abrv
                )
            )

        total = db.scalar(select(func.count()).select_from(query.subquery()))

        items = (
            query.order_by(UnidadMedida.Nombre)
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {"total": total or 0, "data": items}

    def list_select(self, db: Session, q: str | None = None) -> list[tuple[int, str | None, str | None]]:
        query = db.query(UnidadMedida.Id, UnidadMedida.Nombre, UnidadMedida.Abrv)  # <-- incluye Abrv
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    func.lower(UnidadMedida.Nombre).like(func.lower(like)),
                    func.lower(UnidadMedida.Abrv).like(func.lower(like)),
                )
            )
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
        abrv = (payload.Abrv or "").strip() or None  # <-- opcional
        obj = UnidadMedida(Nombre=name, Abrv=abrv)   # <-- guarda abreviatura
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, um_id: int, payload: UnidadMedidaUpdate) -> UnidadMedida:
        obj = self.get(db, um_id)
        name = (payload.Nombre or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Nombre requerido")
        abrv = (payload.Abrv or "").strip() or None  # <-- opcional
        obj.Nombre = name
        obj.Abrv = abrv                              # <-- actualiza abreviatura
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, um_id: int) -> None:
        obj = self.get(db, um_id)
        db.delete(obj)
        db.commit()
