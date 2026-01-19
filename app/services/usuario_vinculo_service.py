from __future__ import annotations
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from sqlalchemy import delete, select
from fastapi import HTTPException
from app.core.roles import ADMIN  # "ADMINISTRADOR"
from app.db.models.identity import AspNetUser, AspNetRole, AspNetUserRole
from app.db.models.usuarios_instituciones import UsuarioInstitucion
from app.db.models.usuarios_divisiones import UsuarioDivision
from app.db.models.usuarios_unidades import UsuarioUnidad
from app.db.models.usuarios_servicios import UsuarioServicio  
from app.db.models.servicio import Servicio  
from app.db.models.unidad import Unidad



Log = logging.getLogger(__name__)


class UsuarioVinculoService:
    # --------- helpers ---------
    def _ensure_user(self, db: Session, user_id: str) -> AspNetUser:
        user = db.get(AspNetUser, user_id)
        if not user:
            Log.warning("Usuario no encontrado en _ensure_user: %s", user_id)
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return user

    def _roles_by_user(self, db: Session, user_id: str) -> list[str]:
        q = (
            db.query(AspNetRole.Name)
              .join(AspNetUserRole, AspNetUserRole.RoleId == AspNetRole.Id)
              .filter(AspNetUserRole.UserId == user_id)
              .order_by(AspNetRole.Name)
        )
        roles = [r[0] for r in q.all()]
        Log.debug("Roles para usuario %s: %s", user_id, roles)
        return roles

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

        Log.debug(
            "Detalle vínculos usuario %s -> inst=%s srv=%s div=%s uni=%s",
            user_id, inst_ids, srv_ids, div_ids, uni_ids,
        )

        return user, roles, inst_ids, srv_ids, div_ids, uni_ids

    # --------- helpers para normalizar ids ---------
    @staticmethod
    def _normalize_ids(raw_ids: list[int] | None) -> list[int]:
        """
        Normaliza la lista de IDs:
        - convierte a int
        - filtra None y <= 0
        - deduplica
        - ordena para que sea más fácil de leer en los logs
        """
        if not raw_ids:
            return []
        norm = {int(i) for i in raw_ids if i is not None and int(i) > 0}
        return sorted(norm)

    # --------- replace sets (borra todo y vuelve a insertar) ---------
    def set_instituciones(self, db: Session, user_id: str, ids: list[int]) -> list[int]:
        self._ensure_user(db, user_id)
        norm_ids = self._normalize_ids(ids)
        Log.info("set_instituciones user_id=%s raw_ids=%s norm_ids=%s", user_id, ids, norm_ids)

        db.execute(delete(UsuarioInstitucion).where(UsuarioInstitucion.UsuarioId == user_id))
        for i in norm_ids:
            db.add(UsuarioInstitucion(UsuarioId=user_id, InstitucionId=i))
        db.commit()

        final_ids = [r.InstitucionId for r in db.query(UsuarioInstitucion).filter_by(UsuarioId=user_id).all()]
        Log.info("set_instituciones user_id=%s persisted_ids=%s", user_id, final_ids)
        return final_ids

    def set_servicios(self, db: Session, user_id: str, ids: list[int]) -> list[int]:
        self._ensure_user(db, user_id)
        norm_ids = self._normalize_ids(ids)
        Log.info("set_servicios user_id=%s raw_ids=%s norm_ids=%s", user_id, ids, norm_ids)

        db.execute(delete(UsuarioServicio).where(UsuarioServicio.UsuarioId == user_id))
        for i in norm_ids:
            db.add(UsuarioServicio(UsuarioId=user_id, ServicioId=i))
        db.commit()

        final_ids = [r.ServicioId for r in db.query(UsuarioServicio).filter_by(UsuarioId=user_id).all()]
        Log.info("set_servicios user_id=%s persisted_ids=%s", user_id, final_ids)
        return final_ids
    
    def set_servicios_scoped(self, db: Session, user_id: str, ids: list[int], actor: UserPublic) -> list[int]:
        """
        ADMIN: puede asignar cualquier ServicioId
        GESTOR_SERVICIOS: solo puede asignar servicios dentro de su alcance (UsuariosServicios del actor)
        """
        self._ensure_user(db, user_id)
        norm_ids = self._normalize_ids(ids)

        if ADMIN in (actor.roles or []):
            return self.set_servicios(db, user_id, norm_ids)

        allowed = self._allowed_servicios_for_actor(db, actor.id)

        forbidden = [i for i in norm_ids if i not in allowed]
        if forbidden:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "forbidden_scope",
                    "msg": "No puedes asignar servicios fuera de tu alcance",
                    "forbidden": forbidden,
                    "allowed": sorted(allowed),
                },
            )

        return self.set_servicios(db, user_id, norm_ids)
    
    def set_divisiones(self, db: Session, user_id: str, ids: list[int]) -> list[int]:
        self._ensure_user(db, user_id)
        norm_ids = self._normalize_ids(ids)
        Log.info("set_divisiones user_id=%s raw_ids=%s norm_ids=%s", user_id, ids, norm_ids)

        db.execute(delete(UsuarioDivision).where(UsuarioDivision.UsuarioId == user_id))
        for i in norm_ids:
            db.add(UsuarioDivision(UsuarioId=user_id, DivisionId=i))
        db.commit()

        final_ids = [r.DivisionId for r in db.query(UsuarioDivision).filter_by(UsuarioId=user_id).all()]
        Log.info("set_divisiones user_id=%s persisted_ids=%s", user_id, final_ids)
        return final_ids

    def set_unidades(self, db: Session, user_id: str, ids: list[int]) -> list[int]:
        """
        Reemplaza unidades vinculadas y además loguea explícitamente
        lo que quedó en la tabla inmediatamente después del commit.
        """
        self._ensure_user(db, user_id)
        norm_ids = self._normalize_ids(ids)
        Log.info("set_unidades user_id=%s raw_ids=%s norm_ids=%s", user_id, ids, norm_ids)

        # borra vínculos previos
        db.execute(delete(UsuarioUnidad).where(UsuarioUnidad.UsuarioId == user_id))
        # inserta nuevos
        for i in norm_ids:
            db.add(UsuarioUnidad(UsuarioId=user_id, UnidadId=i))
        db.commit()

        # verificación post-commit directamente con SELECT
        rows = db.execute(
            select(UsuarioUnidad.UsuarioId, UsuarioUnidad.UnidadId)
            .where(UsuarioUnidad.UsuarioId == user_id)
        ).all()
        Log.info("set_unidades user_id=%s rows_after_commit=%s", user_id, rows)

        final_ids = [r.UnidadId for r in db.query(UsuarioUnidad).filter_by(UsuarioId=user_id).all()]
        Log.info("set_unidades user_id=%s persisted_ids=%s", user_id, final_ids)
        return final_ids

    # --------- activar/desactivar ---------
    def set_active(self, db: Session, user_id: str, active: bool, actor_id: str | None = None) -> AspNetUser:
        user = self._ensure_user(db, user_id)

        # Idempotente
        if user.Active is not None and bool(user.Active) == bool(active):
            Log.info("set_active sin cambios para user_id=%s (estado ya era %s)", user_id, active)
            return user

        user.Active = bool(active)
        user.UpdatedAt = datetime.utcnow()
        user.ModifiedBy = actor_id
        db.commit()
        db.refresh(user)
        Log.info("set_active user_id=%s active=%s actor_id=%s", user_id, active, actor_id)
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
        Log.debug("to_full_dto user_id=%s payload_keys=%s", user.Id, list(base.keys()))
        return base
    
    # --------- activar/desactivar  SETEO DE ROLES---------
    def set_roles(self, db: Session, user_id: str, role_names: list[str]) -> list[str]:
        self._ensure_user(db, user_id)

        norm = sorted({(r or "").strip().upper() for r in (role_names or []) if (r or "").strip()})
        Log.info("set_roles user_id=%s roles=%s", user_id, norm)

        # Trae roles válidos
        rows = db.execute(
            select(AspNetRole.Id, AspNetRole.Name, AspNetRole.NormalizedName)
            .where((AspNetRole.NormalizedName.in_(norm)) | (AspNetRole.Name.in_(norm)))
        ).all()

        # Map por normalizado
        found_norm = set()
        role_ids = []
        for rid, name, nname in rows:
            rn = (nname or name or "").strip().upper()
            if rn:
                found_norm.add(rn)
                role_ids.append(rid)

        missing = [r for r in norm if r not in found_norm]
        if missing:
            raise HTTPException(status_code=400, detail=f"Roles no existen: {missing}")

        # Reemplaza
        db.execute(delete(AspNetUserRole).where(AspNetUserRole.UserId == user_id))
        for rid in role_ids:
            db.add(AspNetUserRole(UserId=user_id, RoleId=rid))
        db.commit()

        return self._roles_by_user(db, user_id)
    

    def _allowed_servicios_for_actor(self, db: Session, actor_id: str) -> set[int]:
        rows = db.execute(
            select(UsuarioServicio.ServicioId).where(UsuarioServicio.UsuarioId == actor_id)
        ).all()
        return {int(r[0]) for r in rows if r and r[0] is not None}

    def set_instituciones_scoped(self, db: Session, user_id: str, ids: list[int], actor: UserPublic) -> list[int]:
        """
        ADMIN: puede asignar cualquier InstitucionId
        GESTOR_SERVICIOS: solo instituciones derivadas de sus servicios:
          allowed_instituciones = DISTINCT Servicios.InstitucionId WHERE Servicios.Id IN (allowed_servicios)
        """
        self._ensure_user(db, user_id)
        norm_ids = self._normalize_ids(ids)

        if ADMIN in (actor.roles or []):
            return self.set_instituciones(db, user_id, norm_ids)

        allowed_servicios = self._allowed_servicios_for_actor(db, actor.id)

        if not allowed_servicios:
            if norm_ids:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "forbidden_scope", "msg": "Gestor sin servicios asignados"},
                )
            return self.set_instituciones(db, user_id, [])

        rows = db.execute(
            select(Servicio.InstitucionId).where(Servicio.Id.in_(sorted(allowed_servicios)))
        ).all()
        allowed_inst = {int(r[0]) for r in rows if r and r[0] is not None}

        forbidden = [i for i in norm_ids if i not in allowed_inst]
        if forbidden:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "forbidden_scope",
                    "msg": "No puedes asignar instituciones fuera de tu alcance (derivado de tus servicios)",
                    "forbidden": forbidden,
                    "allowed": sorted(allowed_inst),
                },
            )

        return self.set_instituciones(db, user_id, norm_ids)

    def usuarios_vinculados_por_servicio_scoped(
        self,
        db,
        target_user_id: str,
        actor: UserPublic,
    ):
        """
        Retorna usuarios que comparten al menos un Servicio con target_user_id.
        Además, incluye ServicioIds = servicios EN COMÚN entre cada usuario y el target.

        Scoped:
        - ADMIN: sin restricción (usa todos los servicios del target)
        - Gestores: solo ve usuarios dentro de servicios que el actor tiene asignados.
                Además, el target debe estar en el scope del actor (si no, 403).
        """

        actor_roles = actor.roles or []
        is_admin = ROLE_ADMIN in actor_roles

        # -----------------------------
        # 1) Servicios del target
        # -----------------------------
        target_srv_sq = (
            select(UsuarioServicio.ServicioId)
            .where(UsuarioServicio.UsuarioId == target_user_id)
        )

        # -----------------------------
        # 2) Scope para no-admin
        # -----------------------------
        if not is_admin:
            actor_srv_sq = (
                select(UsuarioServicio.ServicioId)
                .where(UsuarioServicio.UsuarioId == actor.id)
            )

            # Intersección: servicios que comparten actor y target
            allowed_srv_sq = (
                select(distinct(UsuarioServicio.ServicioId))
                .where(UsuarioServicio.ServicioId.in_(target_srv_sq))
                .where(UsuarioServicio.ServicioId.in_(actor_srv_sq))
            )

            # Si no comparten servicios => fuera de alcance
            any_allowed = db.execute(select(allowed_srv_sq.exists())).scalar()
            if not any_allowed:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "forbidden_scope",
                        "msg": "No puedes consultar usuarios vinculados de este usuario (fuera de tu alcance por servicios).",
                        "target_user_id": target_user_id,
                    },
                )

            srv_filter_sq = allowed_srv_sq
        else:
            # admin: puede usar todos los servicios del target
            srv_filter_sq = target_srv_sq

        # -----------------------------
        # 3) Usuarios vinculados (candidatos):
        #    usuarios que están en algún servicio permitido
        # -----------------------------
        candidates_q = (
            select(distinct(AspNetUser.Id), AspNetUser)
            .join(UsuarioServicio, UsuarioServicio.UsuarioId == AspNetUser.Id)
            .where(UsuarioServicio.ServicioId.in_(srv_filter_sq))
            .where(AspNetUser.Id != target_user_id)
            .order_by(AspNetUser.Apellidos, AspNetUser.Nombres)
        )

        rows = db.execute(candidates_q).all()
        users = [r[1] for r in rows]
        user_ids = [u.Id for u in users]
        if not user_ids:
            return []

        # -----------------------------
        # 4) Servicios EN COMÚN entre cada usuario y el target:
        #    Para cada user_id:
        #      common = (servicios de user) ∩ (servicios del target)
        #    *y además filtrado por srv_filter_sq cuando no-admin (scope real)
        # -----------------------------
        # Creamos un set "filtrable" de target services:
        # - Admin: target_srv_sq
        # - No-admin: igual target_srv_sq, pero también restringimos al srv_filter_sq
        common_services_q = (
            select(
                UsuarioServicio.UsuarioId.label("UsuarioId"),
                UsuarioServicio.ServicioId.label("ServicioId"),
            )
            .where(UsuarioServicio.UsuarioId.in_(user_ids))
            .where(UsuarioServicio.ServicioId.in_(target_srv_sq))
        )

        # Si no-admin, aseguramos que esos comunes estén dentro del scope permitido
        # (si admin, srv_filter_sq == target_srv_sq así que no afecta)
        common_services_q = common_services_q.where(UsuarioServicio.ServicioId.in_(srv_filter_sq))

        common_rows = db.execute(common_services_q).all()

        # Mapa: user_id -> [servicio_ids]
        common_map: dict[str, list[int]] = {}
        for r in common_rows:
            uid = r.UsuarioId
            sid = int(r.ServicioId)
            common_map.setdefault(uid, []).append(sid)

        # Normaliza (orden + unique por si acaso)
        for uid, sids in common_map.items():
            common_map[uid] = sorted(set(sids))

        # -----------------------------
        # 5) Return: lista de dicts
        # -----------------------------
        out = []
        for u in users:
            out.append(
                {
                    "user": u,
                    "ServicioIds": common_map.get(u.Id, []),
                }
            )

        return out
    
    def set_unidades_scoped(self, db: Session, user_id: str, ids: list[int], actor: UserPublic) -> list[int]:
        """
        ADMIN: puede asignar cualquier UnidadId
        GESTOR_SERVICIOS: solo unidades cuyo ServicioId esté dentro de sus servicios permitidos:
          allowed_unidades = Unidades.Id WHERE Unidades.ServicioId IN (allowed_servicios)
        """
        self._ensure_user(db, user_id)
        norm_ids = self._normalize_ids(ids)

        if ADMIN in (actor.roles or []):
            return self.set_unidades(db, user_id, norm_ids)

        allowed_servicios = self._allowed_servicios_for_actor(db, actor.id)

        if not allowed_servicios:
            if norm_ids:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "forbidden_scope", "msg": "Gestor sin servicios asignados"},
                )
            return self.set_unidades(db, user_id, [])

        rows = db.execute(
            select(Unidad.Id).where(Unidad.ServicioId.in_(sorted(allowed_servicios)))
        ).all()
        allowed_unidades = {int(r[0]) for r in rows if r and r[0] is not None}

        forbidden = [i for i in norm_ids if i not in allowed_unidades]
        if forbidden:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "forbidden_scope",
                    "msg": "No puedes asignar unidades fuera de tu alcance (derivado de tus servicios)",
                    "forbidden": forbidden,
                    "allowed": sorted(allowed_unidades),
                },
            )

        return self.set_unidades(db, user_id, norm_ids)
    
    