from __future__ import annotations
from datetime import datetime, timezone
from typing import Iterable, Sequence, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select, func, exists, and_, String, cast
from fastapi import HTTPException

from app.db.models.empresa_distribuidora import (
    EmpresaDistribuidora,
    EmpresasDistribuidoraComuna,
)

def _now():
    return datetime.now(timezone.utc)

class EmpresaDistribuidoraService:
    # --------- Listas ---------
    def list(
        self,
        db: Session,
        q: str | None,
        page: int,
        page_size: int,
        energetico_id: int | None = None,
        comuna_id: int | None = None,
        active: Optional[bool] = True,
    ) -> Dict[str, Any]:
        """
        Retorna:
          - total: cantidad de elementos que cumplen el filtro
          - data: lista de entidades (se mapean a DTO en la ruta)
        """
        base = select(EmpresaDistribuidora)

        # Soft-delete aware (usar == True/False para SQL Server; evita 'IS 1')
        if active is not None:
            base = base.where(EmpresaDistribuidora.Active == active)

        # Búsqueda por texto (case-insensitive) sobre columna TEXT: CAST + LOWER
        if q:
            q_like = f"%{q.lower()}%"
            base = base.where(
                func.lower(cast(EmpresaDistribuidora.Nombre, String)).like(q_like)
            )
            # Si también quieres buscar por RUT, descomenta:
            # from sqlalchemy import or_
            # base = base.where(
            #     or_(
            #         func.lower(cast(EmpresaDistribuidora.Nombre, String)).like(q_like),
            #         func.lower(cast(EmpresaDistribuidora.RUT, String)).like(q_like),
            #     )
            # )

        if energetico_id is not None:
            base = base.where(EmpresaDistribuidora.EnergeticoId == energetico_id)

        if comuna_id is not None:
            sub = (
                select(EmpresasDistribuidoraComuna.Id)
                .where(
                    and_(
                        EmpresasDistribuidoraComuna.EmpresaDistribuidoraId
                            == EmpresaDistribuidora.Id,
                        EmpresasDistribuidoraComuna.ComunaId == comuna_id,
                        # ¡OJO!: usar == True para evitar 'IS 1'
                        EmpresasDistribuidoraComuna.Active == True,
                    )
                )
                .limit(1)
            )
            base = base.where(exists(sub))

        total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

        items = (
            db.execute(
                base.order_by(EmpresaDistribuidora.Nombre)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
            )
            .scalars()
            .all()
        )

        return {"total": total, "data": items}

    def list_select(self, db: Session, energetico_id: int | None = None):
        base = (
            select(EmpresaDistribuidora.Id, EmpresaDistribuidora.Nombre)
            .where(EmpresaDistribuidora.Active == True)  # evita IS 1
            .order_by(EmpresaDistribuidora.Nombre)
        )
        if energetico_id is not None:
            base = base.where(EmpresaDistribuidora.EnergeticoId == energetico_id)
        return db.execute(base).all()

    # --------- CRUD ---------
    def get(self, db: Session, id: int) -> EmpresaDistribuidora:
        obj = db.get(EmpresaDistribuidora, id)
        if not obj:
            raise HTTPException(status_code=404, detail="Empresa distribuidora no encontrada")
        return obj

    def get_detail(self, db: Session, id: int):
        obj = self.get(db, id)
        comuna_ids = (
            db.execute(
                select(EmpresasDistribuidoraComuna.ComunaId)
                .where(EmpresasDistribuidoraComuna.EmpresaDistribuidoraId == id)
                .where(EmpresasDistribuidoraComuna.Active == True)  # evita IS 1
            )
            .scalars()
            .all()
        )
        return obj, list(comuna_ids)

    def create(self, db: Session, data, created_by: str | None) -> EmpresaDistribuidora:
        now = _now()
        obj = EmpresaDistribuidora(
            CreatedAt=now,
            UpdatedAt=now,
            Version=1,
            Active=True,
            OldId=0,
            CreatedBy=created_by,
            ModifiedBy=created_by,
            **{k: v for k, v in data.model_dump(exclude={"ComunaIds"}).items()},
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)

        if getattr(data, "ComunaIds", None):
            self._replace_comunas(db, obj.Id, data.ComunaIds)
        return obj

    def update(self, db: Session, id: int, data, modified_by: str | None) -> EmpresaDistribuidora:
        obj = self.get(db, id)
        patch = data.model_dump(exclude_unset=True, exclude={"ComunaIds"})
        for k, v in patch.items():
            setattr(obj, k, v)
        obj.UpdatedAt = _now()
        obj.ModifiedBy = modified_by
        obj.Version = (obj.Version or 0) + 1
        db.commit()
        db.refresh(obj)

        if "ComunaIds" in data.model_fields_set and data.ComunaIds is not None:
            self._replace_comunas(db, id, data.ComunaIds)
        return obj

    def soft_delete(self, db: Session, id: int, modified_by: str | None) -> None:
        obj = self.get(db, id)
        if obj.Active:
            obj.Active = False
            obj.UpdatedAt = _now()
            obj.ModifiedBy = modified_by
            obj.Version = (obj.Version or 0) + 1
            db.commit()

    def reactivate(self, db: Session, id: int, modified_by: str | None) -> EmpresaDistribuidora:
        obj = self.get(db, id)
        if not obj.Active:
            obj.Active = True
            obj.UpdatedAt = _now()
            obj.ModifiedBy = modified_by
            obj.Version = (obj.Version or 0) + 1
            db.commit()
            db.refresh(obj)
        return obj

    # --------- Comunas (N:M) ---------
    def list_comunas(self, db: Session, empresa_id: int) -> Sequence[int]:
        return (
            db.execute(
                select(EmpresasDistribuidoraComuna.ComunaId)
                .where(EmpresasDistribuidoraComuna.EmpresaDistribuidoraId == empresa_id)
                .where(EmpresasDistribuidoraComuna.Active == True)  # evita IS 1
            )
            .scalars()
            .all()
        )

    def set_comunas(self, db: Session, empresa_id: int, comuna_ids: Iterable[int]):
        self._replace_comunas(db, empresa_id, comuna_ids)
        return self.list_comunas(db, empresa_id)

    def _replace_comunas(self, db: Session, empresa_id: int, comuna_ids: Iterable[int]):
        now = _now()
        # borra todas
        db.query(EmpresasDistribuidoraComuna).filter(
            EmpresasDistribuidoraComuna.EmpresaDistribuidoraId == empresa_id
        ).delete(synchronize_session=False)

        # inserta nuevas
        objs = [
            EmpresasDistribuidoraComuna(
                EmpresaDistribuidoraId=empresa_id,
                ComunaId=int(cid),
                CreatedAt=now,
                UpdatedAt=now,
                Version=1,
                Active=True,
            )
            for cid in (comuna_ids or [])
        ]
        if objs:
            db.add_all(objs)
        db.commit()
