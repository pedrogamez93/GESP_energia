# app/services/institucion_service.py
from typing import List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from fastapi import HTTPException, status

from app.db.models.institucion import Institucion, UsuarioInstitucion
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
        rows = (
            self.db.execute(
                select(Institucion)
                .where(Institucion.Active == True)
                .order_by(Institucion.Nombre.asc())
            )
            .scalars()
            .all()
        )
        return [InstitucionListDTO.model_validate(r) for r in rows]

    def get_by_user_id(self, user_id: str) -> List[InstitucionListDTO]:
        # Admin ve todas
        if self._is_admin_by_user_id(user_id):
            return self.get_all_active()

        # No admin: sólo asociadas y activas
        q = (
            select(Institucion)
            .join(UsuarioInstitucion, UsuarioInstitucion.InstitucionId == Institucion.Id)
            .where(
                Institucion.Active == True,
                UsuarioInstitucion.UsuarioId == user_id,
            )
            .order_by(Institucion.Nombre.asc())
        )
        rows = self.db.execute(q).scalars().all()
        return [InstitucionListDTO.model_validate(r) for r in rows]

    def get_by_id(self, institucion_id: int) -> Institucion:
        return self._get_or_404(institucion_id)

    # ---------- comandos (CRUD) ----------
    def create(self, data: InstitucionCreate) -> InstitucionDTO:
        inst = Institucion(Nombre=data.Nombre, Active=True)
        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return InstitucionDTO.model_validate(inst)

    def update(self, institucion_id: int, data: InstitucionUpdate) -> InstitucionDTO:
        inst = self._get_or_404(institucion_id)
        inst.Nombre = data.Nombre
        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return InstitucionDTO.model_validate(inst)

    def soft_delete(self, institucion_id: int) -> InstitucionDTO:
        inst = self._get_or_404(institucion_id)
        if not inst.Active:
            # ya estaba inactiva: respondemos 200 con el estado actual para idempotencia
            return InstitucionDTO.model_validate(inst)
        inst.Active = False
        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return InstitucionDTO.model_validate(inst)

    def reactivate(self, institucion_id: int) -> InstitucionDTO:
        inst = self._get_or_404(institucion_id)
        if inst.Active:
            return InstitucionDTO.model_validate(inst)
        inst.Active = True
        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return InstitucionDTO.model_validate(inst)
