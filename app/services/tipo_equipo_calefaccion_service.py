# app/services/tipo_equipo_calefaccion_service.py
from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from typing import Optional, Dict, Any

from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_equipo_calefaccion_energetico import (
    TipoEquipoCalefaccionEnergetico,
)
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
            like = f"%{q.strip()}%".lower()
            query = query.filter(func.lower(TipoEquipoCalefaccion.Nombre).like(like))
        total = query.count()
        items = (
            query.order_by(TipoEquipoCalefaccion.Nombre, TipoEquipoCalefaccion.Id)
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return {"total": total, "page": page, "page_size": size, "items": items}

    def get(self, db: Session, id_: int) -> TipoEquipoCalefaccion:
        obj = (
            db.query(TipoEquipoCalefaccion)
            .filter(TipoEquipoCalefaccion.Id == id_)
            .first()
        )
        if not obj:
            raise HTTPException(
                status_code=404, detail="Tipo de equipo de calefacción no encontrado"
            )
        return obj

    def create(
        self, db: Session, data: TipoEquipoCalefaccionCreate, user: str | None = None
    ) -> TipoEquipoCalefaccion:
        """
        Crea usando exclusivamente los campos del modelo/DB.
        (Se eliminaron CreatedAt/UpdatedAt/Version/Active/CreatedBy/ModifiedBy que no existen en la tabla)
        """
        payload: Dict[str, Any] = data.model_dump()

        values: Dict[str, Any] = {
            # obligatorios con fallback para evitar NULL
            "Nombre": _clean_nombre(payload.get("Nombre")),
            "Rendimiento": payload.get("Rendimiento", 0) or 0,
            "A": payload.get("A", 0) or 0,
            "B": payload.get("B", 0) or 0,
            "C": payload.get("C", 0) or 0,
            "Temp": payload.get("Temp", 0) or 0,
            "Costo": payload.get("Costo", 0) or 0,
            "Costo_Social": payload.get("Costo_Social", 0) or 0,
            "Costo_Mant": payload.get("Costo_Mant", 0) or 0,
            "Costo_Social_Mant": payload.get("Costo_Social_Mant", 0) or 0,
            "Ejec_HD_Maestro": payload.get("Ejec_HD_Maestro", 0) or 0,
            "Ejec_HD_Ayte": payload.get("Ejec_HD_Ayte", 0) or 0,
            "Ejec_HD_Jornal": payload.get("Ejec_HD_Jornal", 0) or 0,
            "Mant_HD_Maestro": payload.get("Mant_HD_Maestro", 0) or 0,
            "Mant_HD_Ayte": payload.get("Mant_HD_Ayte", 0) or 0,
            "Mant_HD_Jornal": payload.get("Mant_HD_Jornal", 0) or 0,
            "AC": bool(payload.get("AC", False)),
            "CA": bool(payload.get("CA", False)),
            "FR": bool(payload.get("FR", False)),
        }

        obj = TipoEquipoCalefaccion(**values)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(
        self, db: Session, id_: int, data: TipoEquipoCalefaccionUpdate, user: str | None = None
    ) -> TipoEquipoCalefaccion:
        """
        Actualiza únicamente columnas reales del modelo.
        """
        obj = self.get(db, id_)
        updates = data.model_dump(exclude_unset=True)

        if "Nombre" in updates:
            obj.Nombre = _clean_nombre(updates["Nombre"])

        # Campos numéricos/booleanos
        for k in (
            "Rendimiento",
            "A",
            "B",
            "C",
            "Temp",
            "Costo",
            "Costo_Social",
            "Costo_Mant",
            "Costo_Social_Mant",
            "Ejec_HD_Maestro",
            "Ejec_HD_Ayte",
            "Ejec_HD_Jornal",
            "Mant_HD_Maestro",
            "Mant_HD_Ayte",
            "Mant_HD_Jornal",
            "AC",
            "CA",
            "FR",
        ):
            if k in updates and updates[k] is not None:
                setattr(obj, k, updates[k])

        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id_: int) -> None:
        obj = self.get(db, id_)
        db.delete(obj)
        db.commit()

    # ----- N:M con Energéticos (mantenedor de compatibilidades) -----
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
