from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.db.models.medidor import Medidor
from app.db.models.medidor_division import MedidorDivision

MDIV_TBL = MedidorDivision.__table__


class MedidorDivisionService:
    def list_by_division(self, db: Session, division_id: int) -> List[MedidorDivision]:
        return (
            db.query(MedidorDivision)
            .filter(MedidorDivision.DivisionId == division_id)
            .order_by(MedidorDivision.Id)
            .all()
        )

    def list_divisiones_by_medidor(self, db: Session, medidor_id: int) -> List[int]:
        rows = (
            db.query(MedidorDivision.DivisionId)
            .filter(MedidorDivision.MedidorId == medidor_id)
            .all()
        )
        return [r[0] for r in rows]

    def replace_for_division(self, db: Session, division_id: int, medidor_ids: Iterable[int]) -> List[MedidorDivision]:
        db.execute(delete(MDIV_TBL).where(MDIV_TBL.c.DivisionId == division_id))

        now = datetime.utcnow()
        payload = [
            {
                "CreatedAt": now, "UpdatedAt": now, "Version": 0, "Active": True,
                "ModifiedBy": None, "CreatedBy": None,
                "DivisionId": int(division_id), "MedidorId": int(mid),
            }
            for mid in (medidor_ids or [])
        ]
        if payload:
            db.execute(MDIV_TBL.insert(), payload)
        db.commit()

        return (
            db.query(MedidorDivision)
            .filter(MedidorDivision.DivisionId == division_id)
            .order_by(MedidorDivision.Id)
            .all()
        )
