from __future__ import annotations
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from fastapi import HTTPException

from app.db.models.medidor import Medidor
from app.db.models.medidor_division import MedidorDivision

class MedidorVinculoService:
    # -------- helpers ----------
    def _ensure_medidor(self, db: Session, medidor_id: int) -> Medidor:
        obj = db.get(Medidor, medidor_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Medidor no encontrado")
        return obj

    # -------- consultas ----------
    def medidores_por_division(self, db: Session, division_id: int) -> List[Medidor]:
        # vía tabla N-N
        ids = [
            r[0] for r in db.execute(
                select(MedidorDivision.MedidorId).where(MedidorDivision.DivisionId == division_id)
            ).all()
        ]
        if not ids:
            return []
        return (
            db.query(Medidor)
              .filter(Medidor.Id.in_(ids))
              .order_by(Medidor.Numero, Medidor.Id)
              .all()
        )

    def medidores_por_numero_cliente(self, db: Session, num_cliente_id: int) -> List[Medidor]:
        return (
            db.query(Medidor)
              .filter(Medidor.NumeroClienteId == num_cliente_id)
              .order_by(Medidor.Numero, Medidor.Id)
              .all()
        )

    # -------- escrituras ----------
    def set_divisiones_para_medidor(self, db: Session, medidor_id: int, division_ids: list[int]) -> list[int]:
        self._ensure_medidor(db, medidor_id)

        # Replace-all
        db.execute(delete(MedidorDivision).where(MedidorDivision.MedidorId == medidor_id))

        now = datetime.utcnow()
        for did in sorted(set(division_ids or [])):
            db.add(MedidorDivision(
                CreatedAt=now, UpdatedAt=now, Version=0, Active=True,
                CreatedBy=None, ModifiedBy=None,
                MedidorId=int(medidor_id), DivisionId=int(did),
            ))

        db.commit()

        # devolver lo que quedó persistido
        return [
            r[0] for r in db.execute(
                select(MedidorDivision.DivisionId).where(MedidorDivision.MedidorId == medidor_id)
            ).all()
        ]
