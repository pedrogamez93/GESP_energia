# app/services/tipo_equipo_calefaccion_service.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db.models.tipo_equipo_calefaccion import TipoEquipoCalefaccion
from app.db.models.tipo_equipo_calefaccion_energetico import TipoEquipoCalefaccionEnergetico


def _now():
    return datetime.utcnow()


class TipoEquipoCalefaccionService:
    # ----- Catálogo -----
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        page = max(1, int(page or 1))
        size = max(1, min(200, int(page_size or 50)))

        query = db.query(TipoEquipoCalefaccion)
        if q:
            like = f"%{q}%"
            query = query.filter(
                func.lower(TipoEquipoCalefaccion.Nombre).like(func.lower(like))
            )

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
                status_code=404,
                detail="Tipo de equipo de calefacción no encontrado",
            )
        return obj

    def create(self, db: Session, data, user: str | None = None):
        # Acepta payloads de Pydantic v2 (model_dump) o dict-like
        p = data.model_dump() if hasattr(data, "model_dump") else dict(data)

        values = {
            "Nombre": (p.get("Nombre") or "").strip() or None,
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

        # Blindaje: solo columnas reales
        allowed = {c.key for c in TipoEquipoCalefaccion.__table__.columns}
        values = {k: v for k, v in values.items() if k in allowed}

        obj = TipoEquipoCalefaccion(**values)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # PUT clásico
    def update(self, db: Session, id_: int, data, user: str | None = None):
        """
        PUT /api/v1/tipos-equipos-calefaccion/{id}

        Ahora SÍ actualiza también las banderas AC / CA / FR
        (clasificación para Calefacción, Refrigeración y ACS).
        """
        obj = self.get(db, id_)

        # Pydantic v2 -> usamos model_dump(exclude_unset=True) si existe
        if hasattr(data, "model_dump"):
            p = data.model_dump(exclude_unset=True)
        else:
            p = {k: v for k, v in dict(data).items() if v is not None}

        # Nombre
        if "Nombre" in p:
            obj.Nombre = (p["Nombre"] or "").strip() or None

        # Activo (si la columna existe en el modelo)
        if "Active" in p and hasattr(obj, "Active"):
            if p["Active"] is not None:
                obj.Active = bool(p["Active"])

        # Clasificación: AC (ACS), CA (Calefacción), FR (Refrigeración)
        for flag in ("AC", "CA", "FR"):
            if flag in p and p[flag] is not None:
                setattr(obj, flag, bool(p[flag]))

        # Si quisieras permitir actualizar otros campos numéricos vía PUT,
        # podrías añadirlos aquí de forma explícita.

        db.commit()
        db.refresh(obj)
        return obj

    # PATCH parcial: actualiza cualquier campo recibido
    def update_fields(self, db: Session, id_: int, data, user: str | None = None):
        obj = self.get(db, id_)

        if hasattr(data, "model_dump"):
            p = data.model_dump(exclude_unset=True)  # Pydantic v2
        else:
            # diccionario: ignora claves con None/ausentes
            p = {k: v for k, v in dict(data).items() if v is not None}

        allowed = {c.key for c in TipoEquipoCalefaccion.__table__.columns}
        bools = {"AC", "CA", "FR"}

        for k, v in p.items():
            if k not in allowed:
                continue
            if k == "Nombre":
                v = (v or "").strip() or None
            if k in bools and v is not None:
                v = bool(v)
            setattr(obj, k, v)

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
            .filter(
                TipoEquipoCalefaccionEnergetico.TipoEquipoCalefaccionId == tipo_id
            )
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
            TipoEquipoCalefaccionId=tipo_id,
            EnergeticoId=energetico_id,
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
