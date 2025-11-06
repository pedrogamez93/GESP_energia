from __future__ import annotations

from sqlalchemy import func
from fastapi import HTTPException

from sqlalchemy.orm import Session, load_only
from app.db.models.tipo_colector import TipoColector  # tu modelo

from app.db.models.tipo_colector import TipoColector

class TipoColectorService:
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        page = max(1, int(page or 1))
        size = max(1, min(200, int(page_size or 50)))

        # Filtro base
        filters = []
        if q and isinstance(q, str) and q.strip():
            like = f"%{q.strip()}%"
            filters.append(func.lower(TipoColector.Nombre).like(func.lower(like)))

        # 👉 total sin tocar todas las columnas
        total = db.query(func.count(TipoColector.Id)).filter(*filters).scalar() or 0

        # 👉 items trayendo sólo Id/Nombre
        items = (
            db.query(TipoColector)
              .options(load_only(TipoColector.Id, TipoColector.Nombre))
              .filter(*filters)
              .order_by(TipoColector.Nombre, TipoColector.Id)
              .offset((page - 1) * size)
              .limit(size)
              .all()
        )
        return {"total": total, "page": page, "page_size": size, "items": items}

    def get(self, db: Session, id_: int) -> TipoColector:
        obj = db.query(TipoColector).filter(TipoColector.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Tipo de colector no encontrado")
        return obj

    def create(self, db: Session, data, user: str | None = None):
        # acepta pydantic v2 o dict-like
        p = data.model_dump() if hasattr(data, "model_dump") else dict(data)

        values = {
            "Nombre": (p.get("Nombre") or "").strip() or None,
            "Eta0": p.get("Eta0", 0) or 0,
            "A1": p.get("A1", 0) or 0,
            "A2": p.get("A2", 0) or 0,
            "AreaApertura": p.get("AreaApertura", 0) or 0,
            "Costo": p.get("Costo", 0) or 0,
            "Costo_Mant": p.get("Costo_Mant", 0) or 0,
            "VidaUtil": p.get("VidaUtil", 0) or 0,
            "Active": bool(p.get("Active", True)),
        }

        allowed = {c.key for c in TipoColector.__table__.columns}
        values = {k: v for k, v in values.items() if k in allowed}

        obj = TipoColector(**values)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # PUT “simple” (usado por grillas genéricas de Nombre/Active)
    def update(self, db: Session, id_: int, data, user: str | None = None):
        obj = self.get(db, id_)
        if hasattr(data, "Nombre"):
            obj.Nombre = (data.Nombre or "").strip()
        if hasattr(data, "Active") and data.Active is not None and hasattr(obj, "Active"):
            obj.Active = bool(data.Active)
        db.commit()
        db.refresh(obj)
        return obj

    # PATCH: actualiza cualquier campo enviado
    def update_fields(self, db: Session, id_: int, data, user: str | None = None):
        obj = self.get(db, id_)
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else {
            k: v for k, v in dict(data).items() if v is not None
        }

        allowed = {c.key for c in TipoColector.__table__.columns}
        for k, v in payload.items():
            if k not in allowed:
                continue
            if k == "Nombre":
                v = (v or "").strip() or None
            setattr(obj, k, v)

        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id_: int):
        obj = self.get(db, id_)
        db.delete(obj)
        db.commit()
