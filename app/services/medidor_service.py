from __future__ import annotations

from datetime import datetime
from typing import Optional, Iterable

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, delete

from app.db.models.medidor import Medidor
from app.db.models.numero_cliente import NumeroCliente
from app.db.models.medidor_division import MedidorDivision
from app.db.models.compra_medidor import CompraMedidor

MDIV_TBL = MedidorDivision.__table__


class MedidorService:
    # ---------------- Listado / lecturas ----------------
    def list(
        self,
        db: Session,
        q: Optional[str],
        page: int,
        page_size: int,
        numero_cliente_id: Optional[int] = None,
        division_id: Optional[int] = None,
    ) -> dict:
        query = db.query(Medidor)

        if q:
            like = f"%{q}%"
            query = (
                query.outerjoin(NumeroCliente, NumeroCliente.Id == Medidor.NumeroClienteId)
                .filter(
                    func.lower(func.coalesce(Medidor.Numero, "")).like(func.lower(like)) |
                    func.lower(func.coalesce(NumeroCliente.NombreCliente, "")).like(func.lower(like))
                )
            )

        if numero_cliente_id is not None:
            query = query.filter(Medidor.NumeroClienteId == numero_cliente_id)

        if division_id is not None:
            query = query.filter(Medidor.DivisionId == division_id)

        total = query.count()
        items = (
            query.order_by(Medidor.Numero.nullslast(), Medidor.Id)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def by_division(self, db: Session, division_id: int):
        return (
            db.query(Medidor)
            .filter(Medidor.DivisionId == division_id)
            .order_by(Medidor.Numero.nullslast(), Medidor.Id)
            .all()
        )

    def by_numero_cliente(self, db: Session, numero_cliente_id: int):
        return (
            db.query(Medidor)
            .filter(Medidor.NumeroClienteId == numero_cliente_id)
            .order_by(Medidor.Numero.nullslast(), Medidor.Id)
            .all()
        )

    def by_numcliente_and_numero(
        self, db: Session, numero_cliente_id: int, num_medidor: str
    ) -> Optional[Medidor]:
        if not num_medidor:
            return None
        return (
            db.query(Medidor)
            .filter(
                Medidor.NumeroClienteId == numero_cliente_id,
                func.lower(func.coalesce(Medidor.Numero, "")) == func.lower(num_medidor),
            )
            .first()
        )

    def for_compra_by_numcliente_division(
        self, db: Session, numero_cliente_id: int, division_id: int
    ):
        return (
            db.query(Medidor)
            .filter(
                Medidor.NumeroClienteId == numero_cliente_id,
                Medidor.DivisionId == division_id,
                Medidor.Active == True,
            )
            .order_by(Medidor.Numero.nullslast(), Medidor.Id)
            .all()
        )

    def by_compra(self, db: Session, compra_id: int):
        ids = (
            db.query(CompraMedidor.MedidorId)
            .filter(CompraMedidor.CompraId == compra_id)
            .all()
        )
        id_list = [r[0] for r in ids]
        if not id_list:
            return []
        return db.query(Medidor).filter(Medidor.Id.in_(id_list)).order_by(Medidor.Id).all()

    def check_exist(
        self,
        db: Session,
        numero_cliente_id: int,
        numero: str,
        division_id: Optional[int] = None,
    ) -> Optional[Medidor]:
        if not numero:
            return None
        q = db.query(Medidor).filter(
            Medidor.NumeroClienteId == numero_cliente_id,
            func.lower(func.coalesce(Medidor.Numero, "")) == func.lower(numero),
        )
        if division_id is not None:
            q = q.filter(Medidor.DivisionId == division_id)
        return q.first()

    def get(self, db: Session, medidor_id: int) -> Medidor:
        obj = db.query(Medidor).filter(Medidor.Id == medidor_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Medidor no encontrado")
        return obj

    # ---------------- Escrituras ----------------
    def create(self, db: Session, data, created_by: Optional[str]) -> Medidor:
        now = datetime.utcnow()
        obj = Medidor(
            CreatedAt=now,
            UpdatedAt=now,
            Version=0,
            Active=True,
            CreatedBy=created_by,
            ModifiedBy=created_by,
            Numero=data.Numero,
            NumeroClienteId=data.NumeroClienteId,
            Fases=data.Fases or 0,
            Smart=bool(data.Smart),
            Compartido=bool(data.Compartido),
            DivisionId=data.DivisionId,
            Factura=data.Factura,
            Chilemedido=bool(data.Chilemedido),
            DeviceId=data.DeviceId,
            MedidorConsumo=bool(data.MedidorConsumo),
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, medidor_id: int, data, modified_by: Optional[str]) -> Medidor:
        obj = self.get(db, medidor_id)
        for name, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, name, value)
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, medidor_id: int) -> None:
        obj = self.get(db, medidor_id)
        db.delete(obj)
        db.commit()

    # ---------------- N-N con Divisiones (dbo.MedidorDivision) ----------------
    def set_divisiones(self, db: Session, medidor_id: int, division_ids: Iterable[int], actor_id: Optional[str]) -> list[int]:
        db.execute(delete(MDIV_TBL).where(MDIV_TBL.c.MedidorId == medidor_id))
        now = datetime.utcnow()
        payload = [
            {
                "CreatedAt": now,
                "UpdatedAt": now,
                "Version": 0,
                "Active": True,
                "ModifiedBy": actor_id,
                "CreatedBy": actor_id,
                "DivisionId": int(d),
                "MedidorId": int(medidor_id),
            }
            for d in (division_ids or [])
        ]
        if payload:
            db.execute(MDIV_TBL.insert(), payload)
        db.commit()

        return [
            r[0]
            for r in db.query(MedidorDivision.DivisionId)
            .filter(MedidorDivision.MedidorId == medidor_id)
            .all()
        ]
