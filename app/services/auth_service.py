# app/services/auth_service.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models.identity import AspNetUser
from app.core.security import (
    create_access_token,
    LOCKOUT_MAX_FAILED,
    LOCKOUT_WINDOW_MINUTES,
    verify_password_any,
    hash_password,
)
from app.schemas.auth import UserPublic
from app.utils.identity_password import is_aspnet_hash
from app.core.roles import ADMIN as ROLE_ADMIN  # <-- constante "ADMINISTRADOR"


# =============== Utilidades ===============

def _normalize(s: str) -> str:
    # ASP.NET Identity usa UpperInvariant para campos normalizados
    return (s or "").strip().upper()


def find_user_by_username_or_email(db: Session, identifier: str) -> Optional[AspNetUser]:
    """
    Paridad con ASP.NET:
    1) Busca por NormalizedUserName / NormalizedEmail (como Identity).
    2) Fallback por UserName / Email en crudo (por si los normalizados vienen NULL o mal seteados).
    """
    norm = _normalize(identifier)
    return (
        db.query(AspNetUser)
        .filter(
            or_(
                AspNetUser.NormalizedUserName == norm,
                AspNetUser.NormalizedEmail == norm,
                AspNetUser.UserName == identifier,   # fallback
                AspNetUser.Email == identifier,       # fallback
            )
        )
        .first()
    )


def _has_role(user: AspNetUser, role_name: str) -> bool:
    rn = (role_name or "").upper()
    for r in (user.roles or []):
        if ((r.NormalizedName or "").upper() == rn) or ((r.Name or "").upper() == rn):
            return True
    return False


# =============== Políticas de inicio de sesión ===============

def ensure_login_policies(user: AspNetUser):
    """
    Comportamiento como ASP.NET (por defecto) + bypass de lockout para ADMIN:
    - NO exige EmailConfirmed ni 'Validado' para poder iniciar sesión.
    - Respeta 'Active' cuando es False explícito (None = permitido).
    - Respeta 'Lockout' EXCEPTO si el usuario tiene rol ADMINISTRADOR
      (para que el admin pueda “auto-desbloquearse” sin tocar la BD).
    """
    # Active: bloquea sólo si es False explícito
    if user.Active is False:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    # Bypass de lockout para ADMIN
    if _has_role(user, ROLE_ADMIN):
        return

    # Lockout normal para el resto
    if user.LockoutEnabled and user.LockoutEnd:
        now = datetime.now(timezone.utc)
        lockout_end = user.LockoutEnd
        if lockout_end.tzinfo is None:
            lockout_end = lockout_end.replace(tzinfo=timezone.utc)
        if lockout_end > now:
            raise HTTPException(status_code=403, detail="Cuenta bloqueada temporalmente")


def handle_failed_attempt(db: Session, user: AspNetUser):
    user.AccessFailedCount = (user.AccessFailedCount or 0) + 1
    if user.LockoutEnabled and user.AccessFailedCount >= LOCKOUT_MAX_FAILED:
        user.LockoutEnd = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
        user.AccessFailedCount = 0
    db.add(user)
    db.commit()


def handle_success_attempt(db: Session, user: AspNetUser):
    user.AccessFailedCount = 0
    user.LockoutEnd = None
    db.add(user)
    db.commit()


# =============== Login principal ===============

def login_and_issue_token(db: Session, username_or_email: str, password: str):
    user = find_user_by_username_or_email(db, username_or_email)

    # Respuesta genérica para no filtrar existencia
    invalid_exc = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credenciales inválidas")
    if not user or not user.PasswordHash:
        raise invalid_exc

    # Políticas previas
    ensure_login_policies(user)

    # Verificación híbrida (bcrypt local o ASP.NET Identity v2/v3)
    if not verify_password_any(password, user.PasswordHash):
        handle_failed_attempt(db, user)
        raise invalid_exc

    # Éxito: limpiar contadores/lockout
    handle_success_attempt(db, user)

    # Upgrade de hash (opcional): si venía de ASP.NET, migramos a bcrypt local
    try:
        if is_aspnet_hash(user.PasswordHash):
            new_hash = hash_password(password)
            if new_hash and new_hash != user.PasswordHash:
                user.PasswordHash = new_hash
                db.add(user)
                db.commit()
    except Exception:
        db.rollback()

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
