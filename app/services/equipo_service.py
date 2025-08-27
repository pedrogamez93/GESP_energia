from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from fastapi import HTTPException
from app.db.models.equipo import Equipo

class EquipoService:
    def list(
        self,
        db: Session,
        q: Optional[str],
        page: int,
        page_size: int,
        division_id: Optional[int] = None,
        energetico_id: Optional[int] = None,
        direction: Optional[str] = None,
    ) -> dict:
        """
        q: busca en Marca/Modelo (case-insensitive).
        division_id: filtra por DivisionId.
        energetico_id + direction:
            - direction="in"  -> EnergeticoIn == energetico_id
            - direction="out" -> EnergeticoOut == energetico_id
            - None            -> coincide en cualquiera de los dos
        """
        query = db.query(Equipo)

        if q:
            like = f"%{q}%"
            query = query.filter(
                (func.lower(Equipo.Marca).like(func.lower(like))) |
                (func.lower(Equipo.Modelo).like(func.lower(like)))
            )

        if division_id is not None:
            query = query.filter(Equipo.DivisionId == division_id)

        if energetico_id is not None:
            if direction == "in":
                query = query.filter(Equipo.EnergeticoIn == energetico_id)
            elif direction == "out":
                query = query.filter(Equipo.EnergeticoOut == energetico_id)
            else:
                query = query.filter(
                    (Equipo.EnergeticoIn == energetico_id) |
                    (Equipo.EnergeticoOut == energetico_id)
                )

        total = query.count()
        items = (
            query.order_by(Equipo.Marca, Equipo.Modelo, Equipo.Id)
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def get(self, db: Session, equipo_id: int) -> Equipo:
        obj = db.query(Equipo).filter(Equipo.Id == equipo_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Equipo no encontrado")
        return obj

    def create(self, db: Session, data, created_by: str | None = None) -> Equipo:
        now = datetime.utcnow()
        obj = Equipo(
            CreatedAt=now,
            UpdatedAt=now,
            Version=0,
            Active=True,
            CreatedBy=created_by,
            ModifiedBy=created_by,

            TipoTecnologiaId=data.TipoTecnologiaId,
            SistemaId=data.SistemaId,
            ModoOperacionId=data.ModoOperacionId,
            EnergeticoIn=data.EnergeticoIn,
            EnergeticoOut=data.EnergeticoOut,
            DivisionId=data.DivisionId,

            AnyoCompra=data.AnyoCompra,
            HorasUso=data.HorasUso,
            Marca=data.Marca,
            Modelo=data.Modelo,
            Potencia=data.Potencia,
            Cantidad=data.Cantidad,
            Inversion=data.Inversion,
            CostoMantencion=data.CostoMantencion,

            EnergeticInId=data.EnergeticInId,
            EnergeticOutId=data.EnergeticOutId,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, equipo_id: int, data, modified_by: str | None = None) -> Equipo:
        obj = self.get(db, equipo_id)

        for name, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, name, value)

        obj.Version = (obj.Version or 0) + 1
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by

        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, equipo_id: int) -> None:
        obj = self.get(db, equipo_id)
        db.delete(obj)
        db.commit()
