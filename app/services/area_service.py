# app/services/area_service.py
from __future__ import annotations
from datetime import datetime
from typing import Tuple, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import inspect
from app.db.models.area import Area
from app.schemas.areas import AreaCreate, AreaUpdate


class AreaService:
    def __init__(self, db: Session):
        self.db = db

    # ----------------------------
    # Utils
    # ----------------------------
    def _only_mapped(self, model_cls, data: dict) -> dict:
        """
        Deja solo atributos que realmente están mapeados en el modelo SQLAlchemy.
        Evita TypeError por kwargs inválidos (p.ej. Observaciones, Orden).
        """
        mapper = inspect(model_cls)
        allowed = {attr.key for attr in mapper.attrs}
        return {k: v for k, v in data.items() if k in allowed}

    def _sanitize_create(self, data: dict, created_by: str) -> dict:
        now = datetime.utcnow()
        out = {
            "CreatedAt": now,
            "UpdatedAt": now,
            "Version": 1,
            "Active": True,
            "CreatedBy": created_by,
            "ModifiedBy": created_by,
            **data,
        }
        # Superficie en BD es NOT NULL (Numeric(18,2)) -> default a 0 si None
        if out.get("Superficie") is None:
            out["Superficie"] = 0
        return out

    def _sanitize_update(self, obj: Area, data: dict, modified_by: str) -> dict:
        out = {**data}
        # No permitir modificar metacampos inmutables
        out.pop("Id", None)
        out.pop("CreatedAt", None)
        out.pop("CreatedBy", None)

        # Superficie no puede quedar None (columna NOT NULL)
        if "Superficie" in out and out["Superficie"] is None:
            out["Superficie"] = 0

        out["UpdatedAt"] = datetime.utcnow()
        out["ModifiedBy"] = modified_by
        out["Version"] = (obj.Version or 0) + 1
        return out

    # ----------------------------
    # Queries
    # ----------------------------
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
        page = max(1, page)

        # Sin 'Orden' en la tabla; orden estable por Nombre (NULLS LAST) y luego Id
        # SQL Server no soporta nulls_last() nativo, así que ordenamos por IS NULL y luego valor
        # Primero: las no nulas de Nombre, luego Nombre asc, y finalmente Id asc.
        items = (
            q.order_by((Area.Nombre.is_(None)).asc(), Area.Nombre.asc(), Area.Id.asc())
             .offset((page - 1) * size)
             .limit(size)
             .all()
        )
        return total, items

    def list_by_piso(self, piso_id: int, active: Optional[bool] = True) -> List[Area]:
        q = self.db.query(Area).filter(Area.PisoId == piso_id)
        if active is not None:
            q = q.filter(Area.Active == active)
        return q.order_by((Area.Nombre.is_(None)).asc(), Area.Nombre.asc(), Area.Id.asc()).all()

    def get(self, area_id: int) -> Area | None:
        return self.db.query(Area).filter(Area.Id == area_id).first()

    # ----------------------------
    # Mutations
    # ----------------------------
    def create(self, data: AreaCreate, created_by: str) -> Area:
        # Datos desde Pydantic (sin alias extras)
        payload = data.model_dump(exclude_unset=True)
        # Filtrar a solo columnas reales
        payload = self._only_mapped(Area, payload)
        # Defaults/metadatos y sanitización
        payload = self._sanitize_create(payload, created_by)

        obj = Area(**payload)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update_admin(self, area_id: int, data: AreaUpdate, modified_by: str) -> Area | None:
        obj = self.get(area_id)
        if not obj:
            return None

        payload = data.model_dump(exclude_unset=True)
        payload = self._only_mapped(Area, payload)
        payload = self._sanitize_update(obj, payload, modified_by)

        for k, v in payload.items():
            setattr(obj, k, v)

        self.db.add(obj)
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

        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
