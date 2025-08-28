# app/core/guards.py
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.auth import UserPublic
from app.core.security import require_roles          # devuelve UserPublic
from app.db.models.usuarios_servicios import UsuarioServicio
from app.db.models.identity import AspNetRole, AspNetUserRole

DbDep = Annotated[Session, Depends(get_db)]
ADMIN_ROLE_NAME = "ADMINISTRADOR"

def _is_admin(db: Session, user_id: str) -> bool:
    stmt = (
        select(AspNetRole.Name)
        .join(AspNetUserRole, AspNetUserRole.RoleId == AspNetRole.Id)
        .where(AspNetUserRole.UserId == user_id, AspNetRole.Name == ADMIN_ROLE_NAME)
        .limit(1)
    )
    return db.execute(stmt).first() is not None

def require_service_access(servicio_id: int):
    def _dep(
        db: DbDep,
        current_user: Annotated[UserPublic, Depends(require_roles("*"))],  # cualquier autenticado
    ) -> UserPublic:
        if _is_admin(db, current_user.id):
            return current_user
        ok = (
            db.query(UsuarioServicio)
              .filter(UsuarioServicio.UsuarioId == current_user.id,
                      UsuarioServicio.ServicioId == servicio_id)
              .first()
              is not None
        )
        if not ok:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Sin acceso al servicio")
        return current_user
    return _dep
