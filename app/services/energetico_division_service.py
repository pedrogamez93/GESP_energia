from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, delete, and_
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.models.division import Division
from app.db.models.energetico import Energetico
from app.db.models.energetico_division import EnergeticoDivision

ED_TBL = EnergeticoDivision.__table__

def _now():
    # Tu modelo usa timezone=False, devolvemos naive
    return datetime.utcnow()

class EnergeticoDivisionService:
    # ... (deja tus métodos existentes tal cual)

    def assign_to_division(
        self, db: Session, division_id: int, energetico_id: int, numero_cliente_id: Optional[int] = None
    ) -> EnergeticoDivision:
        # Validaciones mínimas
        if not db.query(Division).filter(Division.Id == division_id).first():
            raise HTTPException(status_code=404, detail="División no encontrada")
        if not db.query(Energetico).filter(Energetico.Id == energetico_id).first():
            raise HTTPException(status_code=404, detail="Energético no encontrado")

        # ¿Existe ya esta relación exacta?
        q = (
            db.query(EnergeticoDivision)
              .filter(EnergeticoDivision.DivisionId == division_id)
              .filter(EnergeticoDivision.EnergeticoId == energetico_id)
        )
        if numero_cliente_id is None:
            q = q.filter(EnergeticoDivision.NumeroClienteId.is_(None))
        else:
            q = q.filter(EnergeticoDivision.NumeroClienteId == numero_cliente_id)

        row = q.first()
        now = _now()
        if row:
            row.Active = True
            row.UpdatedAt = now
            row.Version = (row.Version or 0) + 1
            db.commit(); db.refresh(row)
            return row

        new_row = EnergeticoDivision(
            CreatedAt=now,
            UpdatedAt=now,
            Version=0,
            Active=True,
            ModifiedBy=None,
            CreatedBy=None,
            DivisionId=division_id,
            EnergeticoId=energetico_id,
            NumeroClienteId=numero_cliente_id,
        )
        db.add(new_row)
        db.commit(); db.refresh(new_row)
        return new_row

    def unassign_from_division(
        self, db: Session, division_id: int, energetico_id: int, numero_cliente_id: Optional[int] = None
    ) -> int:
        conds = [
            ED_TBL.c.DivisionId == division_id,
            ED_TBL.c.EnergeticoId == energetico_id,
        ]
        if numero_cliente_id is None:
            conds.append(ED_TBL.c.NumeroClienteId.is_(None))
        else:
            conds.append(ED_TBL.c.NumeroClienteId == numero_cliente_id)

        res = db.execute(delete(ED_TBL).where(and_(*conds)))
        db.commit()
        return res.rowcount or 0
