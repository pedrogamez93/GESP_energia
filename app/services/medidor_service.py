from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, delete

from fastapi import HTTPException

from app.db.models.medidor import Medidor
from app.db.models.medidor_division import MedidorDivision

# Si aún no existe el modelo, crea app/db/models/compra_medidor.py (abajo)
try:
    from app.db.models.compra_medidor import CompraMedidor
except Exception:
    CompraMedidor = None  # type: ignore


class MedidorService:
    # -------- util ----------
    @staticmethod
    def _norm(txt: str):
        # normaliza para comparaciones case/space-insensitive
        return func.lower(func.trim(func.coalesce(txt, "")))

    # -------- Listado / filtros ----------
    def list(
        self,
        db: Session,
        q: Optional[str],
        page: int,
        page_size: int,
        numero_cliente_id: Optional[int] = None,
        division_id: Optional[int] = None,
        smart: Optional[bool] = None,
        consumo: Optional[bool] = None,
        chilemedido: Optional[bool] = None,
    ) -> dict:
        query = db.query(Medidor)

        if q:
            like = f"%{q.strip()}%"
            query = query.filter(self._norm(Medidor.Numero).like(func.lower(like)))

        if numero_cliente_id is not None:
            query = query.filter(Medidor.NumeroClienteId == numero_cliente_id)

        if division_id is not None:
            # Soporta ambos: columna directa y relación en tabla puente
            query = (
                query.outerjoin(
                    MedidorDivision,
                    MedidorDivision.MedidorId == Medidor.Id
                )
                .filter(
                    or_(
                        Medidor.DivisionId == division_id,
                        MedidorDivision.DivisionId == division_id
                    )
                )
                .distinct()
            )

        if smart is not None:
            query = query.filter(Medidor.Smart == bool(smart))

        if consumo is not None:
            query = query.filter(Medidor.MedidorConsumo == bool(consumo))

        if chilemedido is not None:
            query = query.filter(Medidor.Chilemedido == bool(chilemedido))

        total = query.count()
        items = (
            query.order_by(Medidor.NumeroClienteId, Medidor.Numero, Medidor.Id)
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    # -------- CRUD ----------
    def get(self, db: Session, medidor_id: int) -> Medidor:
        obj = db.query(Medidor).filter(Medidor.Id == medidor_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Medidor no encontrado")
        return obj

    def create(self, db: Session, data, created_by: str | None = None) -> Medidor:
        # evita duplicados por (NumeroClienteId, Numero [, DivisionId])
        dupe = self.check_exist(db, data.NumeroClienteId, data.Numero, getattr(data, "DivisionId", None))
        if dupe:
            raise HTTPException(status_code=409, detail="Ya existe un medidor con ese número para el cliente/división")

        now = datetime.utcnow()
        obj = Medidor(
            CreatedAt=now, UpdatedAt=now, Version=0, Active=True,
            CreatedBy=created_by, ModifiedBy=created_by,
            NumeroClienteId=data.NumeroClienteId,
            Numero=data.Numero,
            Fases=getattr(data, "Fases", None),
            Smart=getattr(data, "Smart", None),
            Compartido=getattr(data, "Compartido", None),
            DivisionId=getattr(data, "DivisionId", None),
            Factura=getattr(data, "Factura", None),
            Chilemedido=getattr(data, "Chilemedido", None),
            DeviceId=getattr(data, "DeviceId", None),
            MedidorConsumo=getattr(data, "MedidorConsumo", None),
        )
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def update(self, db: Session, medidor_id: int, data, modified_by: str | None = None) -> Medidor:
        obj = self.get(db, medidor_id)

        # si cambia Numero/Division, validar duplicado
        will_num = data.model_dump(exclude_unset=True).get("Numero", obj.Numero)
        will_div = data.model_dump(exclude_unset=True).get("DivisionId", obj.DivisionId)
        dupe = (
            self.check_exist(db, obj.NumeroClienteId, will_num, will_div)
            and self.by_numcliente_and_numero(db, obj.NumeroClienteId, will_num).Id != obj.Id  # type: ignore
        )
        if dupe:
            raise HTTPException(status_code=409, detail="Conflicto: otro medidor ya tiene ese número/división")

        for name, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, name, value)
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit(); db.refresh(obj)
        return obj

    def delete(self, db: Session, medidor_id: int) -> None:
        obj = self.get(db, medidor_id)
        db.delete(obj); db.commit()

    # -------- consultas específicas ----------
    def by_numero_cliente(self, db: Session, numero_cliente_id: int) -> List[Medidor]:
        return (
            db.query(Medidor)
              .filter(Medidor.NumeroClienteId == numero_cliente_id)
              .order_by(Medidor.Numero, Medidor.Id)
              .all()
        )

    def by_division(self, db: Session, division_id: int) -> List[Medidor]:
        return (
            db.query(Medidor)
              .outerjoin(MedidorDivision, MedidorDivision.MedidorId == Medidor.Id)
              .filter(or_(Medidor.DivisionId == division_id, MedidorDivision.DivisionId == division_id))
              .order_by(Medidor.Numero, Medidor.Id)
              .distinct()
              .all()
        )

    def by_numcliente_and_numero(self, db: Session, numero_cliente_id: int, num_medidor: str) -> Medidor | None:
        if not num_medidor:
            return None
        return (
            db.query(Medidor)
              .filter(
                  and_(
                      Medidor.NumeroClienteId == numero_cliente_id,
                      self._norm(Medidor.Numero) == self._norm(num_medidor),
                  )
              )
              .first()
        )

    # -------- para compras ----------
    def for_compra_by_numcliente_division(self, db: Session, numero_cliente_id: int, division_id: int) -> List[Medidor]:
        # Medidores del cliente que sean "globales" (DivisionId NULL) o específicos de la división
        return (
            db.query(Medidor)
              .filter(
                  Medidor.NumeroClienteId == numero_cliente_id,
                  or_(Medidor.DivisionId == None, Medidor.DivisionId == division_id)  # noqa: E711
              )
              .order_by(Medidor.Numero, Medidor.Id)
              .all()
        )

    def by_compra(self, db: Session, compra_id: int) -> List[Medidor]:
        if not CompraMedidor:
            raise HTTPException(status_code=501, detail="Modelo CompraMedidor no disponible")
        return (
            db.query(Medidor)
              .join(CompraMedidor, CompraMedidor.MedidorId == Medidor.Id)
              .filter(CompraMedidor.CompraId == compra_id)
              .order_by(Medidor.Numero, Medidor.Id)
              .all()
        )

    def check_exist(self, db: Session, numero_cliente_id: int, numero: str, division_id: int | None) -> Medidor | None:
        qry = db.query(Medidor).filter(
            Medidor.NumeroClienteId == numero_cliente_id,
            self._norm(Medidor.Numero) == self._norm(numero),
        )
        if division_id is not None:
            qry = qry.filter(or_(Medidor.DivisionId == None, Medidor.DivisionId == division_id))  # noqa: E711
        return qry.first()

    # -------- divisiones (set) ----------
    def list_divisiones(self, db: Session, medidor_id: int) -> List[int]:
        rows = (
            db.query(MedidorDivision.DivisionId)
              .filter(MedidorDivision.MedidorId == medidor_id)
              .all()
        )
        return [r[0] for r in rows]

    def set_divisiones(self, db: Session, medidor_id: int, division_ids: List[int], actor_id: str | None = None) -> List[int]:
        db.execute(delete(MedidorDivision).where(MedidorDivision.MedidorId == medidor_id))
        now = datetime.utcnow()
        for did in set(division_ids or []):
            db.add(MedidorDivision(
                CreatedAt=now, UpdatedAt=now, Version=0, Active=True,
                CreatedBy=actor_id, ModifiedBy=actor_id,
                MedidorId=medidor_id, DivisionId=int(did),
            ))
        db.commit()
        return self.list_divisiones(db, medidor_id)
