# app/services/usuario_vinculo_service.py
from __future__ import annotations
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import delete, select
from fastapi import HTTPException

from app.db.models.identity import AspNetUser, AspNetRole, AspNetUserRole
from app.db.models.usuarios_instituciones import UsuarioInstitucion
from app.db.models.usuarios_divisiones import UsuarioDivision
from app.db.models.usuarios_unidades import UsuarioUnidad
from app.db.models.usuarios_servicios import UsuarioServicio  # ya existe en tu proyecto


class UsuarioVinculoService:
    # --------- helpers ---------
    def _ensure_user(self, db: Session, user_id: str) -> AspNetUser:
        user = db.get(AspNetUser, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return user

    def _roles_by_user(self, db: Session, user_id: str) -> list[str]:
        q = (
            db.query(AspNetRole.Name)
              .join(AspNetUserRole, AspNetUserRole.RoleId == AspNetRole.Id)
              .filter(AspNetUserRole.UserId == user_id)
              .order_by(AspNetRole.Name)
        )
        return [r[0] for r in q.all()]

    # --------- detail ---------
    def get_detail(self, db: Session, user_id: str):
        user = self._ensure_user(db, user_id)

        inst_ids = [r[0] for r in db.execute(
            select(UsuarioInstitucion.InstitucionId).where(UsuarioInstitucion.UsuarioId == user_id)
        ).all()]

        srv_ids = [r[0] for r in db.execute(
            select(UsuarioServicio.ServicioId).where(UsuarioServicio.UsuarioId == user_id)
        ).all()]

        div_ids = [r[0] for r in db.execute(
            select(UsuarioDivision.DivisionId).where(UsuarioDivision.UsuarioId == user_id)
        ).all()]

        uni_ids = [r[0] for r in db.execute(
            select(UsuarioUnidad.UnidadId).where(UsuarioUnidad.UsuarioId == user_id)
        ).all()]

        roles = self._roles_by_user(db, user_id)

        return user, roles, inst_ids, srv_ids, div_ids, uni_ids

    # --------- replace sets (borra todo y vuelve a insertar) ---------
    def set_instituciones(self, db: Session, user_id: str, ids: list[int]) -> list[int]:
        self._ensure_user(db, user_id)
        db.execute(delete(UsuarioInstitucion).where(UsuarioInstitucion.UsuarioId == user_id))
        for i in set(ids or []):
            db.add(UsuarioInstitucion(UsuarioId=user_id, InstitucionId=int(i)))
        db.commit()
        return [r.InstitucionId for r in db.query(UsuarioInstitucion).filter_by(UsuarioId=user_id).all()]

    def set_servicios(self, db: Session, user_id: str, ids: list[int]) -> list[int]:
        self._ensure_user(db, user_id)
        db.execute(delete(UsuarioServicio).where(UsuarioServicio.UsuarioId == user_id))
        for i in set(ids or []):
            db.add(UsuarioServicio(UsuarioId=user_id, ServicioId=int(i)))
        db.commit()
        return [r.ServicioId for r in db.query(UsuarioServicio).filter_by(UsuarioId=user_id).all()]

    def set_divisiones(self, db: Session, user_id: str, ids: list[int]) -> list[int]:
        self._ensure_user(db, user_id)
        db.execute(delete(UsuarioDivision).where(UsuarioDivision.UsuarioId == user_id))
        for i in set(ids or []):
            db.add(UsuarioDivision(UsuarioId=user_id, DivisionId=int(i)))
        db.commit()
        return [r.DivisionId for r in db.query(UsuarioDivision).filter_by(UsuarioId=user_id).all()]

    def set_unidades(self, db: Session, user_id: str, ids: list[int]) -> list[int]:
        self._ensure_user(db, user_id)
        db.execute(delete(UsuarioUnidad).where(UsuarioUnidad.UsuarioId == user_id))
        for i in set(ids or []):
            db.add(UsuarioUnidad(UsuarioId=user_id, UnidadId=int(i)))
        db.commit()
        return [r.UnidadId for r in db.query(UsuarioUnidad).filter_by(UsuarioId=user_id).all()]

    # --------- activar/desactivar ---------
    def set_active(self, db: Session, user_id: str, active: bool, actor_id: str | None = None) -> AspNetUser:
        user = self._ensure_user(db, user_id)

        # Idempotente
        if user.Active is not None and bool(user.Active) == bool(active):
            return user

        user.Active = bool(active)
        user.UpdatedAt = datetime.utcnow()
        user.ModifiedBy = actor_id
        db.commit()
        db.refresh(user)
        return user
    
    def to_full_dto(
        self,
        user: AspNetUser,
        roles: list[str],
        inst_ids: list[int],
        srv_ids: list[int],
        div_ids: list[int],
        uni_ids: list[int],
    ) -> dict:
        """
        Devuelve un dict listo para UserDetailFullDTO con TODAS
        las columnas del usuario + los sets vinculados.
        """
        base = {
            # columnas AspNetUsers (mapeo directo)
            "AccessFailedCount": getattr(user, "AccessFailedCount", None),
            "EmailConfirmed": getattr(user, "EmailConfirmed", None),
            "LockoutEnabled": getattr(user, "LockoutEnabled", None),
            "LockoutEnd": getattr(user, "LockoutEnd", None),
            "PhoneNumberConfirmed": getattr(user, "PhoneNumberConfirmed", None),
            "TwoFactorEnabled": getattr(user, "TwoFactorEnabled", None),
            "Id": str(user.Id),
            "UserName": user.UserName,
            "NormalizedUserName": getattr(user, "NormalizedUserName", None),
            "Email": user.Email,
            "NormalizedEmail": getattr(user, "NormalizedEmail", None),
            "PasswordHash": getattr(user, "PasswordHash", None),
            "SecurityStamp": getattr(user, "SecurityStamp", None),
            "ConcurrencyStamp": getattr(user, "ConcurrencyStamp", None),
            "PhoneNumber": getattr(user, "PhoneNumber", None),
            "Nombres": getattr(user, "Nombres", None),
            "Apellidos": getattr(user, "Apellidos", None),
            "Active": getattr(user, "Active", None),
            "Address": getattr(user, "Address", None),
            "City": getattr(user, "City", None),
            "PostalCode": getattr(user, "PostalCode", None),
            "Cargo": getattr(user, "Cargo", None),
            "Certificado": getattr(user, "Certificado", None),
            "Nacionalidad": getattr(user, "Nacionalidad", None),
            "Rut": getattr(user, "Rut", None),
            "Validado": getattr(user, "Validado", None),
            "OldId": getattr(user, "OldId", None),
            "ComunaId": getattr(user, "ComunaId", None),
            "SexoId": getattr(user, "SexoId", None),
            "NumeroTelefonoOpcional": getattr(user, "NumeroTelefonoOpcional", None),
            "CreatedAt": getattr(user, "CreatedAt", None),
            "CreatedBy": getattr(user, "CreatedBy", None),
            "ModifiedBy": getattr(user, "ModifiedBy", None),
            "UpdatedAt": getattr(user, "UpdatedAt", None),
            # agregados
            "Roles": roles or [],
            "InstitucionIds": inst_ids or [],
            "ServicioIds": srv_ids or [],
            "DivisionIds": div_ids or [],
            "UnidadIds": uni_ids or [],
        }
        return base