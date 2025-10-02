# app/services/role_service.py
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete
from fastapi import HTTPException
from typing import Iterable, Set
from uuid import uuid4

from app.db.models.identity import AspNetUser, AspNetRole, AspNetUserRole
from app.core import roles as R

def _norm(name: str) -> str:
    return (name or "").strip().upper()

def _nombre_amigable(norm: str) -> str:
    mapping = {
        R.ADMIN: "Administrador",
        R.GESTOR_SRV: "Gestor de servicios",
        R.GESTOR_UNID: "Gestor de unidades",
        R.GESTOR_CONS: "Gestor de consulta",
        R.GESTOR_FLOTA: "Gestor de flota",
        R.GESTOR_FU: "Gestor flota-unidad",
    }
    return mapping.get(norm, norm.title().replace("_", " "))

class RoleService:
    # ---------- CRUD Roles básicos ----------
    def list_roles(self, db: Session, q: str | None = None):
        stmt = select(AspNetRole)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(func.lower(AspNetRole.Name).like(func.lower(like)))
        return db.execute(stmt.order_by(AspNetRole.Name)).scalars().all()

    def get_role_by_name(self, db: Session, name: str) -> AspNetRole | None:
        n = _norm(name)
        return db.query(AspNetRole).filter(
            (func.upper(AspNetRole.NormalizedName) == n) |
            (func.upper(AspNetRole.Name) == n)
        ).first()

    def create_role(self, db: Session, name: str) -> AspNetRole:
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Name requerido")
        if self.get_role_by_name(db, name):
            raise HTTPException(status_code=409, detail="El rol ya existe")
        norm = _norm(name)
        role = AspNetRole(
            Id=str(uuid4()),  # generar PK aquí
            Name=name.strip(),
            NormalizedName=norm,
            Nombre=_nombre_amigable(norm),
        )
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    def rename_role(self, db: Session, role_id: str, new_name: str) -> AspNetRole:
        role = db.get(AspNetRole, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Rol no encontrado")
        if not new_name or not new_name.strip():
            raise HTTPException(status_code=400, detail="Name requerido")

        exists = self.get_role_by_name(db, new_name)
        if exists and str(exists.Id) != str(role_id):  # asegurar comparación como string
            raise HTTPException(status_code=409, detail="Ya existe un rol con ese nombre")

        role.Name = new_name.strip()
        role.NormalizedName = _norm(new_name)
        role.Nombre = _nombre_amigable(role.NormalizedName)
        db.commit()
        db.refresh(role)
        return role

    def delete_role(self, db: Session, role_id: str) -> None:
        role = db.get(AspNetRole, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Rol no encontrado")
        db.execute(delete(AspNetUserRole).where(AspNetUserRole.RoleId == role_id))
        db.delete(role)
        db.commit()

    # ---------- User ↔ Roles ----------
    def list_user_roles(self, db: Session, user_id: str) -> list[str]:
        q = (
            db.query(AspNetRole.Name)
              .join(AspNetUserRole, AspNetUserRole.RoleId == AspNetRole.Id)
              .filter(AspNetUserRole.UserId == user_id)
              .order_by(AspNetRole.Name)
        )
        return [r[0] for r in q.all()]

    def add_user_role(self, db: Session, user_id: str, role_name: str) -> list[str]:
        user = db.get(AspNetUser, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        role = self.get_role_by_name(db, role_name)
        if not role:
            raise HTTPException(status_code=404, detail="Rol no encontrado")
        exists = db.query(AspNetUserRole).filter(
            AspNetUserRole.UserId == user_id,
            AspNetUserRole.RoleId == role.Id
        ).first()
        if not exists:
            db.add(AspNetUserRole(UserId=user_id, RoleId=role.Id))
            db.commit()
        return self.list_user_roles(db, user_id)

    def remove_user_role(self, db: Session, user_id: str, role_name: str) -> list[str]:
        role = self.get_role_by_name(db, role_name)
        if not role:
            raise HTTPException(status_code=404, detail="Rol no encontrado")
        db.execute(delete(AspNetUserRole).where(
            AspNetUserRole.UserId == user_id,
            AspNetUserRole.RoleId == role.Id
        ))
        db.commit()
        return self.list_user_roles(db, user_id)

    def set_user_roles(self, db: Session, user_id: str, role_names: list[str],
                       enforce_single_gestor: bool = False) -> list[str]:
        if enforce_single_gestor:
            gestores = [x for x in (role_names or []) if _norm(x) in R.GESTOR_ROLES]
            if len(gestores) != 1:
                raise HTTPException(status_code=400, detail="Debe asignar exactamente 1 tipo de gestor")

        user = db.get(AspNetUser, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        db.execute(delete(AspNetUserRole).where(AspNetUserRole.UserId == user_id))
        for name in role_names or []:
            role = self.get_role_by_name(db, name)
            if role:
                db.add(AspNetUserRole(UserId=user_id, RoleId=role.Id))
        db.commit()
        return self.list_user_roles(db, user_id)

    # ---------- Jerarquía (DependeDelRoleId) ----------
    def _find_role_by_name_or_norm(self, db: Session, name_or_norm: str) -> AspNetRole | None:
        n = _norm(name_or_norm)
        return db.query(AspNetRole).filter(
            (func.upper(AspNetRole.NormalizedName) == n) |
            (func.upper(AspNetRole.Name) == n)
        ).first()

    def _children_of(self, db: Session, parent_id: str) -> list[AspNetRole]:
        return (
            db.query(AspNetRole)
              .filter(AspNetRole.DependeDelRoleId == parent_id)
              .order_by(AspNetRole.Nombre, AspNetRole.Name)
              .all()
        )

    def _descendants_recursive(self, db: Session, parent_names: Iterable[str],
                               seen_ids: Set[str] | None = None) -> list[AspNetRole]:
        seen_ids = seen_ids or set()
        acc: list[AspNetRole] = []
        for nm in parent_names or []:
            parent = self._find_role_by_name_or_norm(db, nm)
            if not parent:
                continue
            stack = self._children_of(db, parent.Id)
            while stack:
                child = stack.pop()
                if child.Id in seen_ids:
                    continue
                seen_ids.add(child.Id)
                acc.append(child)
                stack.extend(self._children_of(db, child.Id))
        return acc

    def assignable_roles_for_current_user(self, db: Session, current_user_id: str) -> list[AspNetRole]:
        user = db.get(AspNetUser, current_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario actual no encontrado")

        current_role_names = (
            db.query(AspNetRole.Name)
              .join(AspNetUserRole, AspNetUserRole.RoleId == AspNetRole.Id)
              .filter(AspNetUserRole.UserId == current_user_id)
              .all()
        )
        current_role_names = [r[0] for r in current_role_names]
        descendants = self._descendants_recursive(db, current_role_names)
        parents = [self._find_role_by_name_or_norm(db, nm) for nm in current_role_names]
        parents = [p for p in parents if p is not None]

        uniq: dict[str, AspNetRole] = {}
        for obj in parents + descendants:
            uniq[str(obj.Id)] = obj
        return list(uniq.values())

    def available_roles_for_user(self, db: Session, target_user_id: str, current_user_id: str) -> list[AspNetRole]:
        assignable = self.assignable_roles_for_current_user(db, current_user_id)
        assignable_norms = {_norm(x.NormalizedName or x.Name or "") for x in assignable}
        target_norms = {
            _norm(r[0]) for r in (
                db.query(AspNetRole.Name)
                  .join(AspNetUserRole, AspNetUserRole.RoleId == AspNetRole.Id)
                  .filter(AspNetUserRole.UserId == target_user_id)
                  .all()
            )
        }
        result = [r for r in assignable if _norm(r.NormalizedName or r.Name or "") not in target_norms]
        return sorted(result, key=lambda r: (r.Nombre or r.Name or ""))

    # ---------- Seed ----------
    def seed_defaults(self, db: Session) -> list[str]:
        creados = []
        for norm in R.ALL_ROLES:
            if not self.get_role_by_name(db, norm):
                db.add(AspNetRole(
                    Id=str(uuid4()),  # generar PK en seed también
                    Name=norm.title().replace("_", " "),
                    NormalizedName=norm,
                    Nombre=_nombre_amigable(norm),
                ))
                creados.append(norm)
        db.commit()
        return creados
