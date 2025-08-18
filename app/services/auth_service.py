from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models.identity import AspNetUser
from app.utils.identity_password import verify_aspnet_password
from app.core.security import create_access_token, LOCKOUT_MAX_FAILED, LOCKOUT_WINDOW_MINUTES
from app.schemas.auth import UserPublic

from sqlalchemy.orm import Session


def _normalize(s: str) -> str:
    # Identity usa UpperInvariant; en la práctica .upper() suele bastar
    return s.strip().upper()

def find_user_by_username_or_email(db: Session, identifier: str) -> AspNetUser | None:
    norm = _normalize(identifier)
    return (
        db.query(AspNetUser)
        .filter(
            (AspNetUser.NormalizedUserName == norm) |
            (AspNetUser.NormalizedEmail == norm)
        )
        .first()
    )

def ensure_login_policies(user: AspNetUser):
    # Activo / validado / email confirmado
    if user.Active is False:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    if user.EmailConfirmed is False:
        raise HTTPException(status_code=403, detail="Correo no confirmado")
    if user.Validado is False:
        raise HTTPException(status_code=403, detail="Usuario no validado")

    # Lockout
    if user.LockoutEnabled and user.LockoutEnd:
        now = datetime.now(timezone.utc)
        if user.LockoutEnd > now:
            raise HTTPException(status_code=403, detail="Cuenta bloqueada temporalmente")

def handle_failed_attempt(db: Session, user: AspNetUser):
    user.AccessFailedCount = (user.AccessFailedCount or 0) + 1
    if user.LockoutEnabled and user.AccessFailedCount >= LOCKOUT_MAX_FAILED:
        user.LockoutEnd = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
        user.AccessFailedCount = 0  # opcional: reset después de bloquear
    db.add(user)
    db.commit()

def handle_success_attempt(db: Session, user: AspNetUser):
    user.AccessFailedCount = 0
    user.LockoutEnd = None
    db.add(user)
    db.commit()

def login_and_issue_token(db: Session, username_or_email: str, password: str):
    user = find_user_by_username_or_email(db, username_or_email)
    # Mensaje genérico para no filtrar existencia del usuario
    invalid_exc = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credenciales inválidas")
    if not user or not user.PasswordHash:
        raise invalid_exc

    # Políticas previas a verificar password (bloqueos activos, etc.)
    ensure_login_policies(user)

    if not verify_aspnet_password(user.PasswordHash, password):
        handle_failed_attempt(db, user)
        raise invalid_exc

    # Éxito: limpiar contadores/lockout
    handle_success_attempt(db, user)

    roles = [r.NormalizedName or r.Name for r in (user.roles or []) if (r.NormalizedName or r.Name)]
    token = create_access_token(
        sub=str(user.Id),
        roles=[r for r in roles if r],
        extra={"email": user.Email or "", "username": user.UserName or ""},
    )

    user_public = UserPublic(
        id=str(user.Id),
        username=user.UserName,
        email=user.Email,
        nombres=user.Nombres,
        apellidos=user.Apellidos,
        roles=roles,
    )
    return token, user_public
