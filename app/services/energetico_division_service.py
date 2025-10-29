# app/services/energetico_division_service.py
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


class EnergeticoDivisionService:
    # ===========================
    # YA EXISTENTES (se mantienen)
    # ===========================
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

        # Limpia set actual
        db.execute(delete(ED_TBL).where(ED_TBL.c.DivisionId == division_id))

        # Inserta nuevo set (si aplica)
        now = datetime.utcnow()  # naive para calzar con timezone=False del modelo
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

    # ==================================
    # NUEVOS (toggle ON/OFF por cada fila)
    # ==================================
    def assign_to_division(
        self, db: Session, division_id: int, energetico_id: int, numero_cliente_id: Optional[int] = None
    ) -> EnergeticoDivision:
        """
        Crea (o re-activa) la relación exacta Division/Energetico/(NumeroClienteId).
        Idempotente: si ya existe, solo actualiza Active/UpdatedAt/Version.
        """
        # Validaciones mínimas
        if not db.query(Division).filter(Division.Id == division_id).first():
            raise HTTPException(status_code=404, detail="División no encontrada")
        if not db.query(Energetico).filter(Energetico.Id == energetico_id).first():
            raise HTTPException(status_code=404, detail="Energético no encontrado")

        # ¿Ya existe esa combinación exacta?
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
        now = datetime.utcnow()

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
        """
        Elimina (hard delete) la relación exacta Division/Energetico/(NumeroClienteId).
        Retorna cantidad de filas afectadas.
        """
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
