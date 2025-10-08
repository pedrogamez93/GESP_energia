from __future__ import annotations
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, literal, literal_column, select

from app.db.models.sistema import Sistema


class SistemaService:
    # -------- Helpers --------
    @staticmethod
    def _safe_like(col, q: str | None):
        if not q:
            return None
        like = f"%{q.strip()}%"
        # lower(coalesce(col,'')) LIKE lower('%q%')
        return func.lower(func.coalesce(col, "")).like(func.lower(like))

    @staticmethod
    def _order_by_nombre_nulls_last(desc: bool = False):
        """
        Emula NULLS LAST compatible con SQL Server SIN parámetros:
        ORDER BY CASE WHEN Nombre IS NULL THEN 1 ELSE 0 END, lower(Nombre) ASC, Id ASC
        """
        nulls_marker = case(
            (Sistema.Nombre.is_(None), literal_column("1")),
            else_=literal_column("0"),
        ).asc()  # siempre primero el marcador asc para dejar NULL al final

        name_ord = func.lower(Sistema.Nombre).desc() if desc else func.lower(Sistema.Nombre).asc()
        id_ord = Sistema.Id.desc() if desc else Sistema.Id.asc()
        return (nulls_marker, name_ord, id_ord)

    @staticmethod
    def _enforce_page(page: int | None, page_size: int | None):
        page = max(1, int(page or 1))
        size = max(1, min(200, int(page_size or 50)))
        return page, size

    # -------- Listado paginado --------
    def list(self, db: Session, q: str | None, page: int, page_size: int) -> dict:
        page, page_size = self._enforce_page(page, page_size)

        query = db.query(Sistema).filter(Sistema.Active == literal(1))  # evita "IS 1"
        pred = self._safe_like(Sistema.Nombre, q)
        if pred is not None:
            query = query.filter(pred)

        # COUNT usando subquery para evitar efectos colaterales de ORDER/LIMIT
        total = db.execute(
            select(func.count()).select_from(query.subquery())
        ).scalar() or 0

        items = (
            query.order_by(*self._order_by_nombre_nulls_last())
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 .all()
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }

    # -------- Select liviano (Id, Nombre) --------
    def list_select(self, db: Session, q: str | None):
        query = db.query(Sistema.Id, Sistema.Nombre).filter(Sistema.Active == literal(1))
        pred = self._safe_like(Sistema.Nombre, q)
        if pred is not None:
            query = query.filter(pred)

        return query.order_by(*self._order_by_nombre_nulls_last()).all()

    # -------- Get --------
    def get(self, db: Session, id_: int) -> Sistema:
        obj = db.query(Sistema).filter(Sistema.Id == id_).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Sistema no encontrado")
        return obj

    # -------- Create --------
    def create(self, db: Session, data, user: str | None = None):
        now = datetime.utcnow()
        obj = Sistema(
            Nombre=(data.Nombre or "").strip(),
            CreatedAt=now,
            UpdatedAt=now,
            Version=1,
            Active=True,
            CreatedBy=user,
            ModifiedBy=user,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # -------- Update --------
    def update(self, db: Session, id_: int, data, user: str | None = None):
        obj = self.get(db, id_)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v if k != "Nombre" else (v or "").strip())
        obj.UpdatedAt = datetime.utcnow()
        obj.Version = (obj.Version or 0) + 1
        if user:
            obj.ModifiedBy = user
        db.commit()
        db.refresh(obj)
        return obj

    # -------- Delete (soft) --------
    def delete(self, db: Session, id_: int, user: str | None = None):
        obj = self.get(db, id_)
        if not obj.Active:
            return
        obj.Active = False
        obj.UpdatedAt = datetime.utcnow()
        obj.Version = (obj.Version or 0) + 1
        if user:
            obj.ModifiedBy = user
        db.commit()
