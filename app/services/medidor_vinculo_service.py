from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

from sqlalchemy.orm import Session
from sqlalchemy import delete, asc, nulls_last  # <- importamos asc y nulls_last

from app.db.models.medidor import Medidor
from app.db.models.medidor_division import MedidorDivision

MDIV_TBL = MedidorDivision.__table__


class MedidorVinculoService:
    # --- consultas ---
    def medidores_por_division(self, db: Session, division_id: int) -> List[Medidor]:
        """
        Retorna los medidores vinculados a una división, ordenados por Numero (NULL al final) y luego por Id.
        """
        # Subconsulta de IDs para evitar traerlos a memoria si fueran muchos
        subq = (
            db.query(MedidorDivision.MedidorId)
            .filter(MedidorDivision.DivisionId == division_id)
            .subquery()
        )

        # Si no hay filas, devolvemos rápido para evitar el SELECT principal
        # (nota: .first() sobre la subconsulta es costoso; mejor un exists(),
        # pero mantenerlo simple: si no hay vínculos no habrá resultados abajo)
        has_any = db.query(MedidorDivision).filter(MedidorDivision.DivisionId == division_id).first()
        if not has_any:
            return []

        return (
            db.query(Medidor)
            .filter(Medidor.Id.in_(subq))
            # ✅ Emulación portable de "NULLS LAST" en SQL Server
            .order_by(
                nulls_last(asc(Medidor.Numero)),
                Medidor.Id,
            )
            .all()
        )

    def medidores_por_numero_cliente(self, db: Session, num_cliente_id: int) -> List[Medidor]:
        """
        Retorna los medidores por NumeroClienteId, ordenados por Numero (NULL al final) y luego por Id.
        """
        return (
            db.query(Medidor)
            .filter(Medidor.NumeroClienteId == num_cliente_id)
            # ✅ Igual corrección aquí
            .order_by(
                nulls_last(asc(Medidor.Numero)),
                Medidor.Id,
            )
            .all()
        )

    # --- escrituras ---
    def set_divisiones_para_medidor(self, db: Session, medidor_id: int, division_ids: Iterable[int]) -> list[int]:
        # Limpiamos vínculos actuales
        db.execute(delete(MDIV_TBL).where(MDIV_TBL.c.MedidorId == medidor_id))

        now = datetime.utcnow()
        payload = [
            {
                "CreatedAt": now, "UpdatedAt": now, "Version": 0, "Active": True,
                "ModifiedBy": None, "CreatedBy": None,
                "DivisionId": int(d), "MedidorId": int(medidor_id),
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
