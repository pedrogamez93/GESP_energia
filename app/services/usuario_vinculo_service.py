from __future__ import annotations

from datetime import datetime
import logging
from typing import Optional, List, Dict, Set

from sqlalchemy.orm import Session
from sqlalchemy import delete, select, distinct
from fastapi import HTTPException

from app.schemas.auth import UserPublic
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
    # ==========================================================
    # Helpers base
    # ==========================================================
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

    def _allowed_servicios_for_actor(self, db: Session, actor_id: str) -> set[int]:
        rows = db.execute(
            select(UsuarioServicio.ServicioId).where(UsuarioServicio.UsuarioId == actor_id)
        ).all()
        return {int(r[0]) for r in rows if r and r[0] is not None}

    def _is_admin(self, actor: UserPublic) -> bool:
        return ADMIN in (actor.roles or [])

    # ==========================================================
    # Detail (sin scope; el scope lo haces en el router si aplica)
    # ==========================================================
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

    # ==========================================================
    # Replace sets (sin scope)
    # ==========================================================
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

        db.execute(delete(UsuarioUnidad).where(UsuarioUnidad.UsuarioId == user_id))
        for i in norm_ids:
            db.add(UsuarioUnidad(UsuarioId=user_id, UnidadId=i))
        db.commit()

        rows = db.execute(
            select(UsuarioUnidad.UsuarioId, UsuarioUnidad.UnidadId)
            .where(UsuarioUnidad.UsuarioId == user_id)
        ).all()
        Log.info("set_unidades user_id=%s rows_after_commit=%s", user_id, rows)

        final_ids = [r.UnidadId for r in db.query(UsuarioUnidad).filter_by(UsuarioId=user_id).all()]
        Log.info("set_unidades user_id=%s persisted_ids=%s", user_id, final_ids)
        return final_ids

    # ==========================================================
    # Scoped sets
    # ==========================================================
    def set_servicios_scoped(self, db: Session, user_id: str, ids: list[int], actor: UserPublic) -> list[int]:
        """
        ADMIN: puede asignar cualquier ServicioId
        Gestores: solo puede asignar servicios dentro de su alcance (UsuariosServicios del actor)
        """
        self._ensure_user(db, user_id)
        norm_ids = self._normalize_ids(ids)

        if self._is_admin(actor):
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

    def set_instituciones_scoped(self, db: Session, user_id: str, ids: list[int], actor: UserPublic) -> list[int]:
        """
        ADMIN: puede asignar cualquier InstitucionId
        Gestores: solo instituciones derivadas de sus servicios:
          allowed_instituciones = DISTINCT Servicios.InstitucionId WHERE Servicios.Id IN (allowed_servicios)
        """
        self._ensure_user(db, user_id)
        norm_ids = self._normalize_ids(ids)

        if self._is_admin(actor):
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

    def set_unidades_scoped(self, db: Session, user_id: str, ids: list[int], actor: UserPublic) -> list[int]:
        """
        ADMIN: puede asignar cualquier UnidadId
        Gestores: solo unidades cuyo ServicioId esté dentro de sus servicios permitidos:
          allowed_unidades = Unidades.Id WHERE Unidades.ServicioId IN (allowed_servicios)
        """
        self._ensure_user(db, user_id)
        norm_ids = self._normalize_ids(ids)

        if self._is_admin(actor):
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

    # ==========================================================
    # Activar / desactivar
    # ==========================================================
    def set_active(self, db: Session, user_id: str, active: bool, actor_id: str | None = None) -> AspNetUser:
        user = self._ensure_user(db, user_id)

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

    # ==========================================================
    # DTO full (lo dejas igual)
    # ==========================================================
    def to_full_dto(
        self,
        user: AspNetUser,
        roles: list[str],
        inst_ids: list[int],
        srv_ids: list[int],
        div_ids: list[int],
        uni_ids: list[int],
    ) -> dict:
        base = {
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
            "Roles": roles or [],
            "InstitucionIds": inst_ids or [],
            "ServicioIds": srv_ids or [],
            "DivisionIds": div_ids or [],
            "UnidadIds": uni_ids or [],
        }
        Log.debug("to_full_dto user_id=%s payload_keys=%s", user.Id, list(base.keys()))
        return base

    # ==========================================================
    # Set roles
    # ==========================================================
    def set_roles(self, db: Session, user_id: str, role_names: list[str]) -> list[str]:
        self._ensure_user(db, user_id)

        norm = sorted({(r or "").strip().upper() for r in (role_names or []) if (r or "").strip()})
        Log.info("set_roles user_id=%s roles=%s", user_id, norm)

        rows = db.execute(
            select(AspNetRole.Id, AspNetRole.Name, AspNetRole.NormalizedName)
            .where((AspNetRole.NormalizedName.in_(norm)) | (AspNetRole.Name.in_(norm)))
        ).all()

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

        db.execute(delete(AspNetUserRole).where(AspNetUserRole.UserId == user_id))
        for rid in role_ids:
            db.add(AspNetUserRole(UserId=user_id, RoleId=rid))
        db.commit()

        return self._roles_by_user(db, user_id)

    # ==========================================================
    # ✅ VINCULADOS POR SERVICIO (SCOPED) + ServicioIds (en común)
    # ==========================================================
    def usuarios_vinculados_por_servicio_scoped(
        self,
        db: Session,
        target_user_id: str,
        actor: UserPublic,
    ):
        """
        Retorna usuarios que comparten al menos un Servicio con target_user_id.
        Además, incluye ServicioIds = servicios EN COMÚN entre cada usuario y el target.

        Scoped:
        - ADMIN: sin restricción (usa todos los servicios del target)
        - Gestores (GESTOR_SERVICIO / GESTOR DE CONSULTA):
            * Solo ve usuarios dentro de servicios que el actor tiene asignados.
            * El target debe estar dentro del scope del actor (si no, 403).
        """

        # 0) valida target existe
        self._ensure_user(db, target_user_id)

        # ✅ usa tu constante real (app.core.roles.ADMIN)
        actor_roles = actor.roles or []
        is_admin = ADMIN in actor_roles

        # ------------------------------------------------------------
        # 1) subquery servicios del target
        # ------------------------------------------------------------
        target_srv_sq = (
            select(UsuarioServicio.ServicioId)
            .where(UsuarioServicio.UsuarioId == target_user_id)
        )

        # MSSQL-safe: target tiene al menos 1 servicio?
        target_has_any = db.execute(
            select(UsuarioServicio.ServicioId)
            .where(UsuarioServicio.UsuarioId == target_user_id)
            .limit(1)  # MSSQL => TOP(1)
        ).first() is not None

        if not target_has_any:
            Log.info("vinculados-por-servicio: target %s no tiene servicios", target_user_id)
            return []

        # ------------------------------------------------------------
        # 2) scope no-admin => allowed services = intersección actor ∩ target
        # ------------------------------------------------------------
        if not is_admin:
            actor_srv_sq = (
                select(UsuarioServicio.ServicioId)
                .where(UsuarioServicio.UsuarioId == actor.id)
            )

            allowed_srv_sq = (
                select(distinct(UsuarioServicio.ServicioId))
                .where(UsuarioServicio.ServicioId.in_(target_srv_sq))
                .where(UsuarioServicio.ServicioId.in_(actor_srv_sq))
            )

            # MSSQL-safe: hay intersección?
            any_allowed = db.execute(
                select(UsuarioServicio.ServicioId)
                .where(UsuarioServicio.ServicioId.in_(allowed_srv_sq))
                .limit(1)
            ).first() is not None

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

        # ------------------------------------------------------------
        # 3) candidatos: usuarios que están en algún servicio permitido
        #    IMPORTANTÍSIMO:
        #    - select(AspNetUser) (solo entity)
        #    - distinct()
        #    - .unique() al scalar() para evitar InvalidRequestError por eager loads
        # ------------------------------------------------------------
        candidates_q = (
            select(AspNetUser)
            .join(UsuarioServicio, UsuarioServicio.UsuarioId == AspNetUser.Id)
            .where(UsuarioServicio.ServicioId.in_(srv_filter_sq))
            .where(AspNetUser.Id != target_user_id)
            .distinct()
            .order_by(AspNetUser.Apellidos, AspNetUser.Nombres)
        )

        # ✅ FIX: unique() obligatorio cuando hay joined eager loads en AspNetUser
        users = db.scalars(candidates_q).unique().all()

        # Normaliza ids como str (GUID)
        user_ids = [str(u.Id) for u in users if getattr(u, "Id", None)]
        if not user_ids:
            return []

        # ------------------------------------------------------------
        # 4) servicios en común (user ∩ target) restringido al scope real
        # ------------------------------------------------------------
        common_services_q = (
            select(
                UsuarioServicio.UsuarioId.label("UsuarioId"),
                UsuarioServicio.ServicioId.label("ServicioId"),
            )
            .where(UsuarioServicio.UsuarioId.in_(user_ids))
            .where(UsuarioServicio.ServicioId.in_(target_srv_sq))
            .where(UsuarioServicio.ServicioId.in_(srv_filter_sq))
        )

        common_rows = db.execute(common_services_q).all()

        # user_id -> [servicio_ids]
        common_map: dict[str, list[int]] = {}
        for r in common_rows:
            uid = str(r.UsuarioId) if getattr(r, "UsuarioId", None) is not None else None
            sid_raw = getattr(r, "ServicioId", None)
            if not uid or sid_raw is None:
                continue
            sid = int(sid_raw)
            common_map.setdefault(uid, []).append(sid)

        # unique + orden
        for uid in list(common_map.keys()):
            common_map[uid] = sorted(set(common_map[uid]))

        # ------------------------------------------------------------
        # 5) salida lista para UserMiniDTO (incluye ServicioIds)
        # ------------------------------------------------------------
        out: list[dict] = []
        for u in users:
            uid = str(u.Id)
            out.append(
                {
                    "Id": uid,
                    "UserName": getattr(u, "UserName", None),
                    "Email": getattr(u, "Email", None),
                    "Nombres": getattr(u, "Nombres", None),
                    "Apellidos": getattr(u, "Apellidos", None),
                    "Active": getattr(u, "Active", None),
                    "ServicioIds": common_map.get(uid, []),
                }
            )

        Log.info(
            "vinculados-por-servicio target=%s actor=%s is_admin=%s -> %s usuarios",
            target_user_id, getattr(actor, "id", None), is_admin, len(out),
        )
        return out
    
    def unidades_vinculadas_scoped(
        self,
        db: Session,
        target_user_id: str,
        actor: UserPublic,
    ) -> list[Unidad]:
        """
        Unidades vinculadas al target user.
        Scoped:
        - ADMIN: ve todas las unidades del target
        - Gestores: solo unidades cuyo ServicioId esté dentro de los servicios del actor.
                Además, el target debe compartir servicios con actor (si no, 403).
        """

        # 0) valida target existe
        self._ensure_user(db, target_user_id)

        is_admin = ADMIN in (actor.roles or [])

        # 1) unidades del target (base query)
        base_q = (
            select(Unidad)
            .join(UsuarioUnidad, UsuarioUnidad.UnidadId == Unidad.Id)
            .where(UsuarioUnidad.UsuarioId == target_user_id)
            .distinct()
            .order_by(Unidad.Id)
        )

        if is_admin:
            # ✅ admin: sin filtros extra
            return db.scalars(base_q).unique().all()

        # 2) gestor: servicios permitidos del actor
        allowed_servicios = self._allowed_servicios_for_actor(db, actor.id)
        if not allowed_servicios:
            # si el gestor no tiene servicios, no puede ver nada
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "forbidden_scope",
                    "msg": "Gestor sin servicios asignados",
                },
            )

        # 3) Validación scope: target comparte al menos 1 servicio con actor (MSSQL-safe sin EXISTS)
        any_shared = db.execute(
            select(UsuarioServicio.ServicioId)
            .where(UsuarioServicio.UsuarioId == target_user_id)
            .where(UsuarioServicio.ServicioId.in_(sorted(allowed_servicios)))
            .limit(1)
        ).first() is not None

        if not any_shared:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "forbidden_scope",
                    "msg": "No puedes consultar las unidades de este usuario (fuera de tu alcance por servicios).",
                    "target_user_id": target_user_id,
                },
            )

        # 4) filtra unidades del target por servicios permitidos del actor
        scoped_q = base_q.where(Unidad.ServicioId.in_(sorted(allowed_servicios)))

        return db.scalars(scoped_q).unique().all()