from __future__ import annotations
from datetime import datetime
from typing import Tuple, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db.models.piso import Piso
from app.schemas.pisos import PisoDTO, PisoListDTO, PisoCreate, PisoUpdate

class PisoService:
    def __init__(self, db: Session):
        self.db = db

    # Listado paginado/filtrado
    def list_paged(
        self,
        page: int = 1,
        page_size: int = 50,
        division_id: Optional[int] = None,
        active: Optional[bool] = True,
    ) -> Tuple[int, List[Piso]]:
        q = self.db.query(Piso)
        if active is not None:
            q = q.filter(Piso.Active == active)
        if division_id is not None:
            q = q.filter(Piso.DivisionId == division_id)

        total = q.count()
        size = max(1, min(200, page_size))
        items = (
            q.order_by(Piso.Orden.asc().nulls_last(), Piso.Id.asc())
             .offset((page - 1) * size)
             .limit(size)
             .all()
        )
        return total, items

    def list_by_division(self, division_id: int, active: Optional[bool] = True) -> List[Piso]:
        q = self.db.query(Piso).filter(Piso.DivisionId == division_id)
        if active is not None:
            q = q.filter(Piso.Active == active)
        return q.order_by(Piso.Orden.asc().nulls_last(), Piso.Id.asc()).all()

    def get(self, piso_id: int) -> Piso | None:
        return self.db.query(Piso).filter(Piso.Id == piso_id).first()

    def create(self, data: PisoCreate, created_by: str) -> Piso:
        now = datetime.utcnow()
        obj = Piso(
            CreatedAt=now, UpdatedAt=now, Version=1, Active=True,
            CreatedBy=created_by, ModifiedBy=created_by,
            **data.model_dump(exclude_unset=True),
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update_admin(self, piso_id: int, data: PisoUpdate, modified_by: str) -> Piso | None:
        obj = self.get(piso_id)
        if not obj:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        obj.Version = (obj.Version or 0) + 1
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def soft_delete(self, piso_id: int, modified_by: str) -> Piso | None:
        obj = self.get(piso_id)
        if not obj:
            return None
        if not obj.Active:
            return obj
        obj.Active = False
        obj.UpdatedAt = datetime.utcnow()
        obj.ModifiedBy = modified_by
        obj.Version = (obj.Version or 0) + 1
        self.db.commit()
        self.db.refresh(obj)
        return obj
