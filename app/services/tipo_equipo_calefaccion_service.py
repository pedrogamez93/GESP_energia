# app/services/tipo_equipo_calefaccion_service.py
from __future__ import annotations
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_equipo_calefaccion_energetico import TipoEquipoCalefaccionEnergetico
from app.schemas.tipo_equipo_calefaccion import (
    TipoEquipoCalefaccionCreate,
    TipoEquipoCalefaccionUpdate,
)

def _clean_nombre(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = v.strip()
    return s or None

class TipoEquipoCalefaccionService:
    # ----- Catálogo -----
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        page = max(1, int(page or 1))
        size = max(1, min(200, int(page_size or 50)))
        query = db.query(TipoEquipoCalefaccion)
        if q:
            like = f"%{q}%"
            query = query.filter(func.lower(TipoEquipoCalefaccion.Nombre).like(func.lower(like)))
        total = query.count()
        items = (
            query.order_by(TipoEquipoCalefaccion.Nombre, TipoEquipoCalefaccion.Id)
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return {"total": total, "page": page, "page_size": size, "items": items}

    def get(self, db: Session, id_: int) -> TipoEquipoCalefaccion:
        obj = db.query(TipoEquipoCalefaccion).filter(TipoEquipoCalefaccion.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Tipo de equipo de calefacción no encontrado")
        return obj

    def create(self, db: Session, data: TipoEquipoCalefaccionCreate, user: str | None = None) -> TipoEquipoCalefaccion:
        """
        Crea usando SOLO columnas reales de la tabla (sin CreatedAt/UpdatedAt/etc).
        Asegura 0/False para campos NOT NULL si no vienen en el payload.
        """
        p: Dict[str, Any] = data.model_dump()

        values: Dict[str, Any] = {
            "Nombre": _clean_nombre(p.get("Nombre")),
            "Rendimiento": p.get("Rendimiento", 0) or 0,
            "A": p.get("A", 0) or 0,
            "B": p.get("B", 0) or 0,
            "C": p.get("C", 0) or 0,
            "Temp": p.get("Temp", 0) or 0,
            "Costo": p.get("Costo", 0) or 0,
            "Costo_Social": p.get("Costo_Social", 0) or 0,
            "Costo_Mant": p.get("Costo_Mant", 0) or 0,
            "Costo_Social_Mant": p.get("Costo_Social_Mant", 0) or 0,
            "Ejec_HD_Maestro": p.get("Ejec_HD_Maestro", 0) or 0,
            "Ejec_HD_Ayte": p.get("Ejec_HD_Ayte", 0) or 0,
            "Ejec_HD_Jornal": p.get("Ejec_HD_Jornal", 0) or 0,
            "Mant_HD_Maestro": p.get("Mant_HD_Maestro", 0) or 0,
            "Mant_HD_Ayte": p.get("Mant_HD_Ayte", 0) or 0,
            "Mant_HD_Jornal": p.get("Mant_HD_Jornal", 0) or 0,
            "AC": bool(p.get("AC", False)),
            "CA": bool(p.get("CA", False)),
            "FR": bool(p.get("FR", False)),
        }

        # Blindaje: eliminar keys que no son columnas de la tabla
        allowed = {c.key for c in TipoEquipoCalefaccion.__table__.columns}
        values = {k: v for k, v in values.items() if k in allowed}

        obj = TipoEquipoCalefaccion(**values)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, id_: int, data: TipoEquipoCalefaccionUpdate, user: str | None = None) -> TipoEquipoCalefaccion:
        obj = self.get(db, id_)

        upd = data.model_dump(exclude_unset=True)

        if "Nombre" in upd:
            obj.Nombre = _clean_nombre(upd["Nombre"])

        for k in (
            "Rendimiento", "A", "B", "C", "Temp", "Costo", "Costo_Social",
            "Costo_Mant", "Costo_Social_Mant", "Ejec_HD_Maestro", "Ejec_HD_Ayte",
            "Ejec_HD_Jornal", "Mant_HD_Maestro", "Mant_HD_Ayte", "Mant_HD_Jornal",
            "AC", "CA", "FR",
        ):
            if k in upd and upd[k] is not None:
                setattr(obj, k, upd[k])

        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id_: int):
        obj = self.get(db, id_)
        db.delete(obj)
        db.commit()

    # ----- N:M con Energéticos -----
    def list_rel(self, db: Session, tipo_id: int):
        self.get(db, tipo_id)  # valida existencia
        return (
            db.query(TipoEquipoCalefaccionEnergetico)
            .filter(TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId == tipo_id)
            .order_by(TipoEquipoCalefaccionEnergetico.Id)
            .all()
        )

    def add_rel(self, db: Session, tipo_id: int, energetico_id: int):
        self.get(db, tipo_id)
        exists = (
            db.query(TipoEquipoCalefaccionEnergetico)
            .filter(
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId == tipo_id,
                TipoEquipoCalefaccionEnergetico.EnergeticoId == energetico_id,
            )
            .first()
        )
        if exists:
            return exists
        obj = TipoEquipoCalefaccionEnergetico(
            TipoEquipoCalefaccionId=tipo_id, EnergeticoId=energetico_id
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete_rel(self, db: Session, rel_id: int):
        obj = (
            db.query(TipoEquipoCalefaccionEnergetico)
            .filter(TipoEquipoCalefaccionEnergetico.Id == rel_id)
            .first()
        )
        if not obj:
            raise HTTPException(status_code=404, detail="Relación no encontrada")
        db.delete(obj)
        db.commit()
