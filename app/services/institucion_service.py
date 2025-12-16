# app/services/institucion_service.py
from typing import List, Optional
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models.institucion import Institucion
from app.db.models.usuarios_instituciones import UsuarioInstitucion
from app.db.models.identity import AspNetUser
from app.schemas.institucion import (
    InstitucionListDTO,
    InstitucionDTO,
    InstitucionCreate,
    InstitucionUpdate,
)


class InstitucionService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- helpers ----------
    def _is_admin_by_user_id(self, user_id: str) -> bool:
        """
        Retorna True si el usuario tiene el rol ADMINISTRADOR.
        """
        user = (
            self.db.query(AspNetUser)
            .options(joinedload(AspNetUser.roles))
            .filter(AspNetUser.Id == user_id)
            .first()
        )
        if not user:
            return False

        roles = [
            (getattr(r, "NormalizedName", None) or getattr(r, "Name", None) or "").upper()
            for r in (user.roles or [])
        ]
        return "ADMINISTRADOR" in roles

    def _get_or_404(self, institucion_id: int) -> Institucion:
        inst = self.db.get(Institucion, institucion_id)
        if not inst:
            raise HTTPException(status_code=404, detail="Institución no encontrada")
        return inst

    # ---------- queries de lectura ----------
    def get_all_active(self) -> List[InstitucionListDTO]:
        # SQL Server (BIT): usar == True para generar "Active = 1"
        q = (
            select(Institucion)
            .where(Institucion.Active == True)  # noqa: E712
            .order_by(Institucion.Nombre.asc())
        )
        rows = self.db.execute(q).scalars().all()
        return [InstitucionListDTO.model_validate(r) for r in rows]

    def get_by_user_id(self, user_id: str) -> List[InstitucionListDTO]:
        # Admin ve todas (activas, como hasta ahora)
        if self._is_admin_by_user_id(user_id):
            return self.get_all_active()

        # No admin: sólo asociadas y activas
        q = (
            select(Institucion)
            .join(UsuarioInstitucion, UsuarioInstitucion.InstitucionId == Institucion.Id)
            .where(
                Institucion.Active == True,  # noqa: E712
                UsuarioInstitucion.UsuarioId == user_id,
            )
            .order_by(Institucion.Nombre.asc())
        )
        rows = self.db.execute(q).scalars().all()
        return [InstitucionListDTO.model_validate(r) for r in rows]

    def get_by_id(self, institucion_id: int) -> Institucion:
        return self._get_or_404(institucion_id)

    # ---------- comandos (CRUD) ----------
    def create(self, data: InstitucionCreate, created_by: Optional[str] = None) -> InstitucionDTO:
        inst = Institucion(
            Nombre=data.Nombre,
            Active=True,
            CreatedBy=created_by,
            ModifiedBy=created_by,
        )
        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return InstitucionDTO.model_validate(inst)

    def update(
        self,
        institucion_id: int,
        data: InstitucionUpdate,
        modified_by: Optional[str] = None,
    ) -> InstitucionDTO:
        inst = self._get_or_404(institucion_id)

        # ⚠️ No descartar False: sólo ignorar None
        for k, v in data.model_dump(exclude_unset=True).items():
            if v is None:
                continue
            setattr(inst, k, v)

        # Auditoría
        inst.UpdatedAt = datetime.utcnow()
        inst.ModifiedBy = modified_by
        inst.Version = (inst.Version or 0) + 1

        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return InstitucionDTO.model_validate(inst)

    def soft_delete(self, institucion_id: int, modified_by: Optional[str] = None) -> InstitucionDTO:
        inst = self._get_or_404(institucion_id)
        if not inst.Active:
            return InstitucionDTO.model_validate(inst)

        inst.Active = False
        inst.UpdatedAt = datetime.utcnow()
        inst.ModifiedBy = modified_by
        inst.Version = (inst.Version or 0) + 1

        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return InstitucionDTO.model_validate(inst)

    def reactivate(self, institucion_id: int, modified_by: Optional[str] = None) -> InstitucionDTO:
        inst = self._get_or_404(institucion_id)
        if inst.Active:
            return InstitucionDTO.model_validate(inst)

        inst.Active = True
        inst.UpdatedAt = datetime.utcnow()
        inst.ModifiedBy = modified_by
        inst.Version = (inst.Version or 0) + 1

        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return InstitucionDTO.model_validate(inst)

    # --------- listado (con include_inactive) ---------
    def get_all(self, include_inactive: bool = False) -> List[InstitucionListDTO]:
        q = select(Institucion).order_by(Institucion.Nombre.asc())
        if not include_inactive:
            # SQL Server (BIT): usar == True para generar "Active = 1"
            q = q.where(Institucion.Active == True)  # noqa: E712

        rows = self.db.execute(q).scalars().all()
        return [InstitucionListDTO.model_validate(r) for r in rows]
