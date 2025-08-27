from __future__ import annotations
from datetime import datetime
from typing import Iterable, List
from sqlalchemy.orm import Session
from sqlalchemy import delete, select

from fastapi import HTTPException
from app.db.models.medidor_inteligente import (
    MedidorInteligente,
    MedidorInteligenteDivision,
    MedidorInteligenteEdificio,
    MedidorInteligenteServicio,
)

class MedidorInteligenteService:
    # -------- CRUD básico --------
    def get(self, db: Session, med_int_id: int) -> MedidorInteligente:
        obj = db.get(MedidorInteligente, med_int_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Medidor inteligente no encontrado")
        return obj

    def find_by_chilemedido(self, db: Session, chile_medido_id: int) -> MedidorInteligente | None:
        return db.query(MedidorInteligente).filter(
            MedidorInteligente.ChileMedidoId == chile_medido_id
        ).first()

    def create(self, db: Session, chile_medido_id: int, created_by: str | None = None) -> MedidorInteligente:
        now = datetime.utcnow()
        obj = MedidorInteligente(
            CreatedAt=now, UpdatedAt=now, Version=0, Active=True,
            CreatedBy=created_by, ModifiedBy=created_by,
            ChileMedidoId=chile_medido_id,
        )
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def update_chilemedido(self, db: Session, med_int_id: int, new_val: int, modified_by: str | None = None) -> MedidorInteligente:
        obj = self.get(db, med_int_id)
        obj.ChileMedidoId = new_val
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit(); db.refresh(obj)
        return obj

    # -------- Vínculos (replace set) --------
    def _replace(self, db: Session, model, med_int_id: int, field: str, ids: Iterable[int]) -> List[int]:
        db.execute(delete(model).where(model.MedidorInteligenteId == med_int_id))
        now = datetime.utcnow()
        for x in set(ids or []):
            db.add(model(
                MedidorInteligenteId=med_int_id,
                **{field: int(x)},
                CreatedAt=now, UpdatedAt=now, Version=0, Active=True
            ))
        db.commit()
        col = getattr(model, field)
        return [r[0] for r in db.execute(select(col).where(model.MedidorInteligenteId == med_int_id)).all()]

    def set_divisiones(self, db: Session, med_int_id: int, ids: Iterable[int]) -> List[int]:
        self.get(db, med_int_id)
        return self._replace(db, MedidorInteligenteDivision, med_int_id, "DivisionId", ids)

    def set_edificios(self, db: Session, med_int_id: int, ids: Iterable[int]) -> List[int]:
        self.get(db, med_int_id)
        return self._replace(db, MedidorInteligenteEdificio, med_int_id, "EdificioId", ids)

    def set_servicios(self, db: Session, med_int_id: int, ids: Iterable[int]) -> List[int]:
        self.get(db, med_int_id)
        return self._replace(db, MedidorInteligenteServicio, med_int_id, "ServicioId", ids)

    # -------- detalle (Ids vinculados) --------
    def get_detail_ids(self, db: Session, med_int_id: int) -> tuple[list[int], list[int], list[int]]:
        self.get(db, med_int_id)
        divs = [r[0] for r in db.execute(
            select(MedidorInteligenteDivision.DivisionId).where(MedidorInteligenteDivision.MedidorInteligenteId == med_int_id)
        ).all()]
        edis = [r[0] for r in db.execute(
            select(MedidorInteligenteEdificio.EdificioId).where(MedidorInteligenteEdificio.MedidorInteligenteId == med_int_id)
        ).all()]
        srvs = [r[0] for r in db.execute(
            select(MedidorInteligenteServicio.ServicioId).where(MedidorInteligenteServicio.MedidorInteligenteId == med_int_id)
        ).all()]
        return divs, edis, srvs
