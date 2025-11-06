# app/services/edificio_service.py
from __future__ import annotations
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from fastapi import HTTPException

from app.db.models.edificio import Edificio


def _display_nombre(e: Edificio) -> str:
    base = (e.Calle or e.Direccion or "").strip()
    num  = (e.Numero or "").strip()
    if base and num:
        return f"{base} {num}"
    return base or num or f"Edificio #{e.Id}"


# Helpers de normalización (evita aplicar lower() a tipos no-string)
def _norm_str(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return str(s).strip().lower()


class EdificioService:
    def list(
        self,
        db: Session,
        q: str | None,
        page: int,
        page_size: int,
        ComunaId: int | None = None,
        active: Optional[bool] = True,
    ) -> dict:
        query = db.query(Edificio)
        if active is not None:
            query = query.filter(Edificio.Active == active)

        if q:
            like = f"%{q.strip().lower()}%"
            # Solo aplicamos lower() a columnas de texto
            query = query.filter(
                func.lower(func.coalesce(Edificio.Calle, "")).like(like) |
                func.lower(func.coalesce(Edificio.Direccion, "")).like(like) |
                func.lower(func.coalesce(Edificio.Numero, "")).like(like)
            )

        if ComunaId is not None:
            query = query.filter(Edificio.ComunaId == ComunaId)

        total = query.count()
        items = (
            query.order_by(Edificio.Calle, Edificio.Numero, Edificio.Id)
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def list_select(self, db: Session, q: str | None, ComunaId: int | None = None) -> List[tuple[int, str]]:
        query = db.query(Edificio).filter(Edificio.Active == True)

        if ComunaId is not None:
            query = query.filter(Edificio.ComunaId == ComunaId)

        if q:
            like = f"%{q.strip().lower()}%"
            query = query.filter(
                func.lower(func.coalesce(Edificio.Calle, "")).like(like) |
                func.lower(func.coalesce(Edificio.Direccion, "")).like(like)
            )

        rows = query.order_by(Edificio.Calle, Edificio.Numero, Edificio.Id).all()
        return [(e.Id, _display_nombre(e)) for e in rows]

    def get(self, db: Session, edificio_id: int) -> Edificio:
        obj = db.query(Edificio).filter(Edificio.Id == edificio_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Edificio no encontrado")
        return obj

    def _exists_same_address(
        self,
        db: Session,
        calle: str | None,
        numero: str | None,
        comuna_id: int | None,
        exclude_id: int | None = None,
    ) -> bool:
        """
        Verifica duplicados evitando SELECT EXISTS de nivel superior,
        que en SQL Server produce 'Incorrect syntax near EXISTS'.
        Usamos COUNT(*) (válido en SQL Server) sobre columnas de texto normalizadas.
        """
        calle_n  = _norm_str(calle)
        numero_n = _norm_str(numero)

        if calle_n is None or numero_n is None or comuna_id is None:
            return False

        filters = [
            func.lower(func.coalesce(Edificio.Calle, "")) == calle_n,
            func.lower(func.coalesce(Edificio.Numero, "")) == numero_n,
            Edificio.ComunaId == comuna_id,
        ]
        if exclude_id:
            filters.append(Edificio.Id != exclude_id)

        dup_count = (
            db.query(func.count())
              .select_from(Edificio)
              .filter(and_(*filters))
              .scalar()
        )
        return bool(dup_count)

    def create(self, db: Session, data: dict, created_by: str | None) -> Edificio:
        calle  = (data.get("Calle") or "").strip()
        numero = (data.get("Numero") or "").strip()
        comuna = data.get("ComunaId")

        if self._exists_same_address(db, calle, numero, comuna):
            raise HTTPException(status_code=409, detail="Ya existe un edificio con esa dirección en la misma comuna.")

        now = datetime.utcnow()
        obj = Edificio(
            CreatedAt=now,
            UpdatedAt=now,
            Version=1,
            Active=True,
            CreatedBy=created_by,
            **(data or {}),
        )
        # Aseguramos campos saneados
        obj.Calle = calle
        obj.Numero = numero

        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, edificio_id: int, data: dict, modified_by: str | None) -> Edificio:
        obj = self.get(db, edificio_id)

        will_calle  = (data.get("Calle", obj.Calle) or "").strip()
        will_numero = (data.get("Numero", obj.Numero) or "").strip()
        will_comuna = data.get("ComunaId", obj.ComunaId)

        if self._exists_same_address(db, will_calle, will_numero, will_comuna, exclude_id=obj.Id):
            raise HTTPException(status_code=409, detail="Ya existe otro edificio con esa dirección en la misma comuna.")

        for k, v in (data or {}).items():
            setattr(obj, k, v)

        # normalizamos los dos campos string críticos
        obj.Calle = will_calle
        obj.Numero = will_numero

        obj.ModifiedBy = modified_by
        obj.UpdatedAt = datetime.utcnow()
        obj.Version = (obj.Version or 0) + 1

        db.commit()
        db.refresh(obj)
        return obj

    def soft_delete(self, db: Session, edificio_id: int, modified_by: str | None) -> None:
        obj = self.get(db, edificio_id)
        if not obj.Active:
            return
        obj.Active = False
        obj.ModifiedBy = modified_by
        obj.UpdatedAt = datetime.utcnow()
        obj.Version = (obj.Version or 0) + 1
        db.commit()

    def reactivate(self, db: Session, edificio_id: int, modified_by: str | None) -> Edificio:
        obj = self.get(db, edificio_id)
        if obj.Active:
            return obj
        obj.Active = True
        obj.ModifiedBy = modified_by
        obj.UpdatedAt = datetime.utcnow()
        obj.Version = (obj.Version or 0) + 1
        db.commit()
        db.refresh(obj)
        return obj
