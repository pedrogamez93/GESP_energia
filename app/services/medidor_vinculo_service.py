from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.db.models.medidor import Medidor
from app.db.models.medidor_division import MedidorDivision

MDIV_TBL = MedidorDivision.__table__


class MedidorVinculoService:
    # --- consultas ---
    def medidores_por_division(self, db: Session, division_id: int) -> List[Medidor]:
        ids = (
            db.query(MedidorDivision.MedidorId)
            .filter(MedidorDivision.DivisionId == division_id)
            .all()
        )
        mid_list = [r[0] for r in ids]
        if not mid_list:
            return []
        return (
            db.query(Medidor)
            .filter(Medidor.Id.in_(mid_list))
            .order_by(Medidor.Numero.nullslast(), Medidor.Id)
            .all()
        )

    def medidores_por_numero_cliente(self, db: Session, num_cliente_id: int) -> List[Medidor]:
        return (
            db.query(Medidor)
            .filter(Medidor.NumeroClienteId == num_cliente_id)
            .order_by(Medidor.Numero.nullslast(), Medidor.Id)
            .all()
        )

    # --- escrituras ---
    def set_divisiones_para_medidor(
        self, db: Session, medidor_id: int, division_ids: Iterable[int]
    ) -> list[int]:
        db.execute(delete(MDIV_TBL).where(MDIV_TBL.c.MedidorId == medidor_id))

        now = datetime.utcnow()
        payload = [
            {
                "CreatedAt": now,
                "UpdatedAt": now,
                "Version": 0,
                "Active": True,
                "ModifiedBy": None,
                "CreatedBy": None,
                "DivisionId": int(d),
                "MedidorId": int(medidor_id),
            }
            for d in (division_ids or [])
        ]
        if payload:
            db.execute(MDIV_TBL.insert(), payload)

        db.commit()
        rows = (
            db.query(MedidorDivision.DivisionId)
            .filter(MedidorDivision.MedidorId == medidor_id)
            .all()
        )
        return [r[0] for r in rows]
