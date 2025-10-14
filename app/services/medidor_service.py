from __future__ import annotations

import time
import logging
from datetime import datetime
from typing import Optional, Iterable

from fastapi import HTTPException
from sqlalchemy import func, case, delete, true
from sqlalchemy.orm import Session

from app.db.models.medidor import Medidor
from app.db.models.numero_cliente import NumeroCliente
from app.db.models.medidor_division import MedidorDivision
from app.db.models.compra_medidor import CompraMedidor
from app.schemas.medidor import MedidorListDTO

MDIV_TBL = MedidorDivision.__table__

log = logging.getLogger("medidores")


def _order_by_numero_nulls_last():
    """
    SQL Server no soporta 'NULLS LAST'.
    Emulamos con: CASE WHEN Numero IS NULL THEN 1 ELSE 0 END, Numero, Id
    """
    nulls_flag = case((Medidor.Numero.is_(None), 1), else_=0)
    return (nulls_flag.asc(), Medidor.Numero.asc(), Medidor.Id.asc())


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

        # Filtros
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

        # Total antes de paginar
        t0 = time.perf_counter()
        total = query.count()
        t1 = time.perf_counter()

        # 🚀 Orden sargable por PK para paginación rápida (NVARCHAR(MAX) en Numero es caro)
        rows = (
            query.order_by(Medidor.Id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        t2 = time.perf_counter()

        items = [MedidorListDTO.model_validate(x) for x in rows]

        log.info(
            "[medidores] count=%s en %.3fs | fetch page=%s size=%s en %.3fs",
            total, (t1 - t0), page, page_size, (t2 - t1),
        )

        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def by_division(self, db: Session, division_id: int):
        return (
            db.query(Medidor)
            .filter(Medidor.DivisionId == division_id)
            .order_by(*_order_by_numero_nulls_last())
            .all()
        )

    def by_numero_cliente(self, db: Session, numero_cliente_id: int):
        return (
            db.query(Medidor)
            .filter(Medidor.NumeroClienteId == numero_cliente_id)
            .order_by(*_order_by_numero_nulls_last())
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
        # ⚠️ MSSQL: usar == true() o == True (NO .is_(True)) para que compile a "= 1"
        return (
            db.query(Medidor)
            .filter(
                Medidor.NumeroClienteId == numero_cliente_id,
                Medidor.DivisionId == division_id,
                Medidor.Active == true(),   # << fix principal para MSSQL
            )
            .order_by(*_order_by_numero_nulls_last())
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
        return (
            db.query(Medidor)
            .filter(Medidor.Id.in_(id_list))
            .order_by(Medidor.Id.asc())
            .all()
        )

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
    def set_divisiones(
        self,
        db: Session,
        medidor_id: int,
        division_ids: Iterable[int],
        actor_id: Optional[str],
    ) -> list[int]:
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
