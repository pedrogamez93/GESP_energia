from __future__ import annotations

from datetime import datetime
from typing import Iterable, Tuple, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.db.models.medidor_inteligente import MedidorInteligente
from app.db.models.medidor_inteligente_links import (
    MedidorInteligenteDivision,
    MedidorInteligenteEdificio,
    MedidorInteligenteServicio,
)

MID_TBL = MedidorInteligenteDivision.__table__
MIE_TBL = MedidorInteligenteEdificio.__table__
MIS_TBL = MedidorInteligenteServicio.__table__


class MedidorInteligenteService:
    # -------- lecturas --------
    def get(self, db: Session, med_int_id: int) -> MedidorInteligente:
        obj = db.query(MedidorInteligente).filter(MedidorInteligente.Id == med_int_id).first()
        if not obj:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="No encontrado")
        return obj

    def find_by_chilemedido(self, db: Session, chilemedido_id: int) -> Optional[MedidorInteligente]:
        return (
            db.query(MedidorInteligente)
            .filter(MedidorInteligente.ChileMedidoId == chilemedido_id)
            .first()
        )

    def get_detail_ids(self, db: Session, med_int_id: int) -> Tuple[List[int], List[int], List[int]]:
        divs = (
            db.query(MedidorInteligenteDivision.DivisionId)
            .filter(MedidorInteligenteDivision.MedidorInteligenteId == med_int_id)
            .all()
        )
        edis = (
            db.query(MedidorInteligenteEdificio.EdificioId)
            .filter(MedidorInteligenteEdificio.MedidorInteligenteId == med_int_id)
            .all()
        )
        srvs = (
            db.query(MedidorInteligenteServicio.ServicioId)
            .filter(MedidorInteligenteServicio.MedidorInteligenteId == med_int_id)
            .all()
        )
        return [r[0] for r in divs], [r[0] for r in edis], [r[0] for r in srvs]

    # -------- escrituras --------
    def create(self, db: Session, chilemedido_id: int, created_by: str | None) -> MedidorInteligente:
        now = datetime.utcnow()
        obj = MedidorInteligente(
            CreatedAt=now, UpdatedAt=now, Version=0, Active=True,
            CreatedBy=created_by, ModifiedBy=created_by,
            ChileMedidoId=chilemedido_id,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update_chilemedido(
        self, db: Session, med_int_id: int, chilemedido_id: int, modified_by: str | None
    ) -> MedidorInteligente:
        obj = self.get(db, med_int_id)
        obj.ChileMedidoId = chilemedido_id
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit()
        db.refresh(obj)
        return obj

    # --- reemplazos atómicos de vínculos ---
    def set_divisiones(self, db: Session, med_int_id: int, division_ids: Iterable[int]) -> list[int]:
        db.execute(delete(MID_TBL).where(MID_TBL.c.MedidorInteligenteId == med_int_id))
        now = datetime.utcnow()
        payload = [
            {
                "CreatedAt": now, "UpdatedAt": now, "Version": 0, "Active": True,
                "ModifiedBy": None, "CreatedBy": None,
                "MedidorInteligenteId": int(med_int_id), "DivisionId": int(d),
            }
            for d in (division_ids or [])
        ]
        if payload:
            db.execute(MID_TBL.insert(), payload)
        db.commit()
        rows = (
            db.query(MedidorInteligenteDivision.DivisionId)
            .filter(MedidorInteligenteDivision.MedidorInteligenteId == med_int_id)
            .all()
        )
        return [r[0] for r in rows]

    def set_edificios(self, db: Session, med_int_id: int, edificio_ids: Iterable[int]) -> list[int]:
        db.execute(delete(MIE_TBL).where(MIE_TBL.c.MedidorInteligenteId == med_int_id))
        now = datetime.utcnow()
        payload = [
            {
                "CreatedAt": now, "UpdatedAt": now, "Version": 0, "Active": True,
                "ModifiedBy": None, "CreatedBy": None,
                "MedidorInteligenteId": int(med_int_id), "EdificioId": int(eid),
            }
            for eid in (edificio_ids or [])
        ]
        if payload:
            db.execute(MIE_TBL.insert(), payload)
        db.commit()
        rows = (
            db.query(MedidorInteligenteEdificio.EdificioId)
            .filter(MedidorInteligenteEdificio.MedidorInteligenteId == med_int_id)
            .all()
        )
        return [r[0] for r in rows]

    def set_servicios(self, db: Session, med_int_id: int, servicio_ids: Iterable[int]) -> list[int]:
        db.execute(delete(MIS_TBL).where(MIS_TBL.c.MedidorInteligenteId == med_int_id))
        now = datetime.utcnow()
        payload = [
            {
                "CreatedAt": now, "UpdatedAt": now, "Version": 0, "Active": True,
                "ModifiedBy": None, "CreatedBy": None,
                "MedidorInteligenteId": int(med_int_id), "ServicioId": int(sid),
            }
            for sid in (servicio_ids or [])
        ]
        if payload:
            db.execute(MIS_TBL.insert(), payload)
        db.commit()
        rows = (
            db.query(MedidorInteligenteServicio.ServicioId)
            .filter(MedidorInteligenteServicio.MedidorInteligenteId == med_int_id)
            .all()
        )
        return [r[0] for r in rows]
