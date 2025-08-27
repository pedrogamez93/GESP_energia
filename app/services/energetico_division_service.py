from __future__ import annotations
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from fastapi import HTTPException
from app.db.models.division import Division
from app.db.models.energetico_division import EnergeticoDivision

ED_TBL = EnergeticoDivision.__table__

class EnergeticoDivisionService:
    def list_by_division(self, db: Session, division_id: int) -> List[EnergeticoDivision]:
        if not db.query(Division).filter(Division.Id == division_id).first():
            raise HTTPException(status_code=404, detail="División no encontrada")
        return (
            db.query(EnergeticoDivision)
              .filter(EnergeticoDivision.DivisionId == division_id)
              .order_by(EnergeticoDivision.EnergeticoId, EnergeticoDivision.Id)
              .all()
        )

    def list_divisiones_by_energetico(self, db: Session, energetico_id: int) -> List[int]:
        rows = db.execute(
            select(ED_TBL.c.DivisionId).where(ED_TBL.c.EnergeticoId == energetico_id)
        ).all()
        return [r[0] for r in rows]

    def replace_for_division(self, db: Session, division_id: int, items: List[dict]) -> List[EnergeticoDivision]:
        if not db.query(Division).filter(Division.Id == division_id).first():
            raise HTTPException(status_code=404, detail="División no encontrada")

        db.execute(delete(ED_TBL).where(ED_TBL.c.DivisionId == division_id))

        now = datetime.utcnow()
        payload = []
        for it in items or []:
            payload.append({
                "CreatedAt": now, "UpdatedAt": now, "Version": 0, "Active": True,
                "ModifiedBy": None, "CreatedBy": None,
                "DivisionId": int(division_id),
                "EnergeticoId": int(it["EnergeticoId"]),
                "NumeroClienteId": int(it["NumeroClienteId"]) if it.get("NumeroClienteId") is not None else None,
            })

        if payload:
            db.execute(ED_TBL.insert(), payload)

        db.commit()
        return self.list_by_division(db, division_id)
