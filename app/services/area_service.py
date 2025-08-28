from __future__ import annotations
from datetime import datetime
from typing import Tuple, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db.models.area import Area
from app.schemas.areas import AreaDTO, AreaListDTO, AreaCreate, AreaUpdate

class AreaService:
    def __init__(self, db: Session):
        self.db = db

    def list_paged(
        self,
        page: int = 1,
        page_size: int = 50,
        piso_id: Optional[int] = None,
        active: Optional[bool] = True,
    ) -> Tuple[int, List[Area]]:
        q = self.db.query(Area)
        if active is not None:
            q = q.filter(Area.Active == active)
        if piso_id is not None:
            q = q.filter(Area.PisoId == piso_id)

        total = q.count()
        size = max(1, min(200, page_size))
        items = (
            q.order_by(Area.Orden.asc().nulls_last(), Area.Id.asc())
             .offset((page - 1) * size)
             .limit(size)
             .all()
        )
        return total, items

    def list_by_piso(self, piso_id: int, active: Optional[bool] = True) -> List[Area]:
        q = self.db.query(Area).filter(Area.PisoId == piso_id)
        if active is not None:
            q = q.filter(Area.Active == active)
        return q.order_by(Area.Orden.asc().nulls_last(), Area.Id.asc()).all()

    def get(self, area_id: int) -> Area | None:
        return self.db.query(Area).filter(Area.Id == area_id).first()

    def create(self, data: AreaCreate, created_by: str) -> Area:
        now = datetime.utcnow()
        obj = Area(
            CreatedAt=now, UpdatedAt=now, Version=1, Active=True,
            CreatedBy=created_by, ModifiedBy=created_by,
            **data.model_dump(exclude_unset=True),
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update_admin(self, area_id: int, data: AreaUpdate, modified_by: str) -> Area | None:
        obj = self.get(area_id)
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

    def soft_delete(self, area_id: int, modified_by: str) -> Area | None:
        obj = self.get(area_id)
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
