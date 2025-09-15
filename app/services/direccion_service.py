# app/services/direccion_service.py
from __future__ import annotations

from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, case

from app.db.models.direccion import Direccion
from app.schemas.direcciones import DireccionCreate, DireccionUpdate


class DireccionService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- Helpers ----------
    @staticmethod
    def _nulls_last(col):
        # Emula NULLS LAST en SQL Server
        return case((col.is_(None), 1), else_=0).asc(), col.asc()

    # ---------- Listado paginado ----------
    def list_paged(
        self,
        page: int = 1,
        page_size: int = 50,
        region_id: Optional[int] = None,
        provincia_id: Optional[int] = None,
        comuna_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Tuple[int, List[Direccion]]:
        q = self.db.query(Direccion)

        if region_id is not None:
            q = q.filter(Direccion.RegionId == region_id)
        if provincia_id is not None:
            q = q.filter(Direccion.ProvinciaId == provincia_id)
        if comuna_id is not None:
            q = q.filter(Direccion.ComunaId == comuna_id)

        if search:
            like = f"%{search}%"
            q = q.filter(or_(
                Direccion.Calle.like(like),
                Direccion.DireccionCompleta.like(like),
                Direccion.Numero.like(like),
            ))

        total = q.count()
        size = max(1, min(200, page_size))

        calle_order = self._nulls_last(Direccion.Calle)
        num_order = self._nulls_last(Direccion.Numero)

        items = (
            q.order_by(
                *calle_order,
                *num_order,
                Direccion.Id.desc(),
            )
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return total, items

    # ---------- CRUD ----------
    def get(self, direccion_id: int) -> Direccion | None:
        return self.db.query(Direccion).filter(Direccion.Id == direccion_id).first()

    def resolve_exact(self, calle: str, numero: str, comuna_id: int) -> Direccion | None:
        return (
            self.db.query(Direccion)
            .filter(
                Direccion.Calle == calle,
                Direccion.Numero == numero,
                Direccion.ComunaId == comuna_id,
            )
            .first()
        )

    def create(self, data: DireccionCreate) -> Direccion:
        obj = Direccion(**data.model_dump(exclude_unset=True))
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, direccion_id: int, data: DireccionUpdate) -> Direccion | None:
        obj = self.get(direccion_id)
        if not obj:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, direccion_id: int) -> bool:
        obj = self.get(direccion_id)
        if not obj:
            return False
        self.db.delete(obj)
        self.db.commit()
        return True
