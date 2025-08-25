from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.db.models.unidad_medida import UnidadMedida
from app.schemas.unidad_medida import (
    UnidadMedidaCreate, UnidadMedidaUpdate
)

class UnidadMedidaService:
    # Lista completa (con búsqueda opcional y paginación simple)
    def list(self, db: Session, q: str | None, page: int, page_size: int):
        base = select(UnidadMedida)
        if q:
            like = f"%{q}%"
            base = base.where(func.lower(UnidadMedida.Nombre).like(func.lower(like)))
        total = db.scalar(select(func.count()).select_from(base.subquery()))
        items = db.execute(
            base.order_by(UnidadMedida.Nombre)
                .offset((page - 1) * page_size)
                .limit(page_size)
        ).scalars().all()
        return {"total": total, "data": items}

    # Lista reducida para selects (Id, Nombre)
    def list_select(self, db: Session):
        result = db.execute(
            select(UnidadMedida.Id, UnidadMedida.Nombre).order_by(UnidadMedida.Nombre)
        )
        rows = result.all()
        return rows or []   # <- evita None por cualquier cambio futuro

    def get(self, db: Session, id: int) -> UnidadMedida:
        obj = db.get(UnidadMedida, id)
        if not obj:
            raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
        return obj

    def create(self, db: Session, data: UnidadMedidaCreate) -> UnidadMedida:
        obj = UnidadMedida(**data.model_dump(exclude_unset=True))
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, id: int, data: UnidadMedidaUpdate) -> UnidadMedida:
        obj = self.get(db, id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return obj

    # El .NET elimina físicamente la fila (Remove + SaveChanges) -> replicamos hard delete
    def delete(self, db: Session, id: int) -> None:
        obj = self.get(db, id)
        db.delete(obj)
        db.commit()
