from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import UserPublic
from app.core.security import require_roles
from app.db.models.usuarios_servicios import UsuarioServicio
from app.core.roles import ADMIN, ADMIN_VARIANTS

DbDep = Annotated[Session, Depends(get_db)]
ADMIN_ROLE_NAME = ADMIN  # "ADMINISTRADOR"

def _is_admin_roles(roles: list[str]) -> bool:
    req = {r.upper() for r in ADMIN_VARIANTS}  # acepta ADMINISTRADOR y ADMINISTRADORR
    have = { (r or "").upper() for r in (roles or []) }
    return not req.isdisjoint(have)

def require_service_access(servicio_id: int):
    """
    Permite acceso si:
      - Es ADMIN (acepta variantes normalizadas), o
      - Existe relación en UsuarioServicio (UsuarioId, ServicioId)
    """
    def _dep(
        db: DbDep,
        current_user: Annotated[UserPublic, Depends(require_roles("*"))],  # cualquier autenticado
    ) -> UserPublic:
        if _is_admin_roles(current_user.roles):
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
