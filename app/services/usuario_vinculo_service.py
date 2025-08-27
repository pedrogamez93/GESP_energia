# app/services/usuario_vinculo_service.py
from __future__ import annotations
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
