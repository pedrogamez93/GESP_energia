from __future__ import annotations
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from fastapi import HTTPException
from app.db.base import Base
from app.db.models.division import Division
from app.db.models.medidor_division import MedidorDivision

_MD_TABLE_KEY = "dbo.MedidorDivision"
def _MD():
    return Base.metadata.tables[_MD_TABLE_KEY]

class MedidorDivisionService:
    def list_by_division(self, db: Session, division_id: int) -> List[MedidorDivision]:
        if not db.query(Division).filter(Division.Id == division_id).first():
            raise HTTPException(status_code=404, detail="División no encontrada")
        return (
            db.query(MedidorDivision)
              .filter(MedidorDivision.DivisionId == division_id)
              .order_by(MedidorDivision.MedidorId, MedidorDivision.Id)
              .all()
        )

    def list_divisiones_by_medidor(self, db: Session, medidor_id: int) -> List[int]:
        rows = db.execute(
            select(_MD().c.DivisionId).where(_MD().c.MedidorId == medidor_id)
        ).all()
        return [r[0] for r in rows]

    def replace_for_division(self, db: Session, division_id: int, medidor_ids: List[int]) -> List[MedidorDivision]:
        if not db.query(Division).filter(Division.Id == division_id).first():
            raise HTTPException(status_code=404, detail="División no encontrada")

        db.execute(delete(_MD()).where(_MD().c.DivisionId == division_id))

        now = datetime.utcnow()
        payload = []
        for mid in sorted(set(medidor_ids or [])):
            payload.append({
                "CreatedAt": now, "UpdatedAt": now, "Version": 0, "Active": True,
                "ModifiedBy": None, "CreatedBy": None,
                "DivisionId": int(division_id),
                "MedidorId": int(mid),
            })
        if payload:
            db.execute(_MD().insert(), payload)

        db.commit()
        return self.list_by_division(db, division_id)
