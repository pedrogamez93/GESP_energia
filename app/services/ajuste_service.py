# app/services/ajuste_service.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models.ajuste import Ajuste
from app.schemas.ajustes import AjustePatchDTO

class AjusteService:
    def __init__(self, db: Session):
        self.db = db

    def _get_or_create(self) -> Ajuste:
        obj = self.db.query(Ajuste).order_by(Ajuste.Id.asc()).first()
        if obj:
            return obj
        now = datetime.utcnow()
        obj = Ajuste(
            CreatedAt=now,
            UpdatedAt=now,
            Version=1,
            Active=True,
            EditUnidadPMG=False,
            DeleteUnidadPMG=False,
            ComprasServicio=False,
            CreateUnidadPMG=False,
            ActiveAlcanceModule=False,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get(self) -> Ajuste:
        return self._get_or_create()

    def patch(self, data: AjustePatchDTO) -> Ajuste:
        obj = self._get_or_create()
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.UpdatedAt = datetime.utcnow()
        obj.Version = (obj.Version or 0) + 1
        self.db.commit()
        self.db.refresh(obj)
        return obj
