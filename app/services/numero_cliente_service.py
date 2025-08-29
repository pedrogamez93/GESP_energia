from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db.models.numero_cliente import NumeroCliente

class NumeroClienteService:
    def list(
        self, db: Session, q: Optional[str], page: int, page_size: int,
        empresa_id: Optional[int] = None, tipo_tarifa_id: Optional[int] = None,
        division_id: Optional[int] = None,
        active: Optional[bool] = True,   # <- NUEVO
    ) -> dict:
        query = db.query(NumeroCliente)
        if active is not None:
            query = query.filter(NumeroCliente.Active == active)

        if q:
            like = f"%{q}%"
            query = query.filter(
                (func.lower(NumeroCliente.Numero).like(func.lower(like))) |
                (func.lower(NumeroCliente.NombreCliente).like(func.lower(like)))
            )

        if empresa_id is not None:
            query = query.filter(NumeroCliente.EmpresaDistribuidoraId == empresa_id)
        if tipo_tarifa_id is not None:
            query = query.filter(NumeroCliente.TipoTarifaId == tipo_tarifa_id)
        if division_id is not None:
            query = query.filter(NumeroCliente.DivisionId == division_id)

        total = query.count()
        items = (
            query.order_by(NumeroCliente.Numero, NumeroCliente.Id)
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def get(self, db: Session, num_cliente_id: int) -> NumeroCliente:
        obj = db.query(NumeroCliente).filter(NumeroCliente.Id == num_cliente_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Número de cliente no encontrado")
        return obj

    def create(self, db: Session, data, created_by: str | None = None) -> NumeroCliente:
        now = datetime.utcnow()
        obj = NumeroCliente(
            CreatedAt=now,
            UpdatedAt=now,
            Version=0,
            Active=True,
            CreatedBy=created_by,
            ModifiedBy=created_by,

            Numero=data.Numero,
            NombreCliente=data.NombreCliente,
            EmpresaDistribuidoraId=data.EmpresaDistribuidoraId,
            TipoTarifaId=data.TipoTarifaId,
            DivisionId=data.DivisionId,
            PotenciaSuministrada=data.PotenciaSuministrada or 0.0,
        )
        db.add(obj); db.commit(); db.refresh(obj)
        return obj

    def update(self, db: Session, num_cliente_id: int, data, modified_by: str | None = None) -> NumeroCliente:
        obj = self.get(db, num_cliente_id)
        for name, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, name, value)
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit(); db.refresh(obj)
        return obj

    def soft_delete(self, db: Session, num_cliente_id: int, modified_by: str | None = None) -> None:
        obj = self.get(db, num_cliente_id)
        if not obj.Active:
            return
        obj.Active = False
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit()

    def reactivate(self, db: Session, num_cliente_id: int, modified_by: str | None = None) -> NumeroCliente:
        obj = self.get(db, num_cliente_id)
        if obj.Active:
            return obj
        obj.Active = True
        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        db.commit(); db.refresh(obj)
        return obj
