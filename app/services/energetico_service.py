from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException
from datetime import datetime, timezone

from app.db.models.energetico import Energetico, EnergeticoUnidadMedida, EnergeticoDivision
from app.schemas.energetico import EnergeticoCreate, EnergeticoUpdate, EnergeticoUMCreate, EnergeticoUMUpdate

def _now():
    return datetime.now(timezone.utc)

class EnergeticoService:
    # ---------- Energeticos ----------
    def list(self, db: Session, q: str | None, page: int, page_size: int):
        base = select(Energetico)
        if q:
            like = f"%{q}%"
            base = base.where(func.lower(Energetico.Nombre).like(func.lower(like)))
        total = db.scalar(select(func.count()).select_from(base.subquery()))
        items = db.execute(
            base.order_by(Energetico.Posicion, Energetico.Nombre)
                .offset((page - 1) * page_size)
                .limit(page_size)
        ).scalars().all()
        return {"total": total, "data": items}

    def list_select(self, db: Session):
        return db.execute(
            select(Energetico.Id, Energetico.Nombre).order_by(Energetico.Posicion, Energetico.Nombre)
        ).all()

    def get(self, db: Session, id: int) -> Energetico:
        obj = db.get(Energetico, id)
        if not obj:
            raise HTTPException(status_code=404, detail="Energético no encontrado")
        return obj

    def create(self, db: Session, data: EnergeticoCreate) -> Energetico:
        now = _now()
        obj = Energetico(
            CreatedAt=now, UpdatedAt=now, Version=1, Active=True,
            **data.model_dump(exclude_unset=True)
        )
        db.add(obj)
        db.commit(); db.refresh(obj)
        return obj

    def update(self, db: Session, id: int, data: EnergeticoUpdate) -> Energetico:
        obj = self.get(db, id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.UpdatedAt = _now()
        obj.Version = (obj.Version or 0) + 1
        db.commit(); db.refresh(obj)
        return obj

    def delete(self, db: Session, id: int) -> None:
        obj = self.get(db, id)
        db.delete(obj)
        db.commit()

    # ---------- Energetico x División ----------
    def by_division(self, db: Session, division_id: int):
        stmt = (
            select(EnergeticoDivision)
            .where(EnergeticoDivision.DivisionId == division_id)
            .where(EnergeticoDivision.Active == True)
        )
        return db.execute(stmt).scalars().all()

    def activos_by_division(self, db: Session, division_id: int):
        # Equivalente a GetEnergeticosActivos (sin la validación de compras)
        stmt = (
            select(Energetico)
            .join(EnergeticoDivision, EnergeticoDivision.EnergeticoId == Energetico.Id)
            .where(EnergeticoDivision.DivisionId == division_id)
            .where(Energetico.Active == True)
            .where(EnergeticoDivision.Active == True)
            .order_by(Energetico.Posicion, Energetico.Nombre)
        )
        return db.execute(stmt).scalars().all()

    # ---------- Unidades de medida por energético ----------
    def list_um(self, db: Session, energetico_id: int):
        stmt = (
            select(EnergeticoUnidadMedida)
            .where(EnergeticoUnidadMedida.EnergeticoId == energetico_id)
            .where(EnergeticoUnidadMedida.Active == True)
        )
        return db.execute(stmt).scalars().all()

    def add_um(self, db: Session, energetico_id: int, data: EnergeticoUMCreate):
        now = _now()
        row = EnergeticoUnidadMedida(
            EnergeticoId=energetico_id, Active=True, Version=1,
            CreatedAt=now, UpdatedAt=now, **data.model_dump(exclude_unset=True)
        )
        db.add(row); db.commit(); db.refresh(row)
        return row

    def update_um(self, db: Session, um_id: int, data: EnergeticoUMUpdate):
        row = db.get(EnergeticoUnidadMedida, um_id)
        if not row:
            raise HTTPException(status_code=404, detail="Relación no encontrada")
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        row.UpdatedAt = _now()
        row.Version = (row.Version or 0) + 1
        db.commit(); db.refresh(row)
        return row

    def delete_um(self, db: Session, um_id: int):
        row = db.get(EnergeticoUnidadMedida, um_id)
        if not row:
            raise HTTPException(status_code=404, detail="Relación no encontrada")
        db.delete(row); db.commit()
