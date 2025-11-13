# app/services/password_reset_service.py
from __future__ import annotations

import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.models.user import User  # AspNetUser alias
from app.db.models.password_reset import PasswordResetToken
from app.utils.hash import Hash  # bcrypt para password

# ─────────────────────────────────────────────────────────────────────────────
# Config & Mail (seguros por defecto)
# ─────────────────────────────────────────────────────────────────────────────
Log = logging.getLogger(__name__)

# Intentamos tomar settings; si no existen, proveemos defaults seguros
try:
    from app.core.config import settings  # type: ignore[attr-defined]
except Exception:
    class _S:  # defaults mínimos para no romper
        PASSWORD_RESET_TTL_MINUTES = 30
        FRONTEND_RESET_URL = "https://tu-frontend/reset-password"
        ROTATE_SECURITY_STAMP = True
        MAIL_FROM = None
        MAIL_SERVER = None
    settings = _S()  # type: ignore

# Intentamos importar el mailer real; si no, usamos stub que solo loguea
try:
    from app.utils.mail import send_password_reset_email
except Exception:  # pragma: no cover
    def send_password_reset_email(to_email: str, reset_link: str) -> None:  # type: ignore
        Log.warning(
            "MAIL stub activo: no se envía correo. to=%s link=%s",
            to_email, reset_link
        )

# TTL configurable con default
RESET_TTL_MINUTES: int = int(getattr(settings, "PASSWORD_RESET_TTL_MINUTES", 30))
FRONTEND_RESET_URL: str = str(getattr(settings, "FRONTEND_RESET_URL", "https://tu-frontend/reset-password"))
ROTATE_SECURITY_STAMP: bool = bool(getattr(settings, "ROTATE_SECURITY_STAMP", True))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de compatibilidad con el modelo (PascalCase/snake_case)
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_attr(cls, *names):
    for n in names:
        if hasattr(cls, n):
            return getattr(cls, n)
    return None

def _resolve_name(cls, *names) -> Optional[str]:
    for n in names:
        if hasattr(cls, n):
            return n
    return None

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


# ─────────────────────────────────────────────────────────────────────────────
# API
# ─────────────────────────────────────────────────────────────────────────────
def create_reset_token(db: Session, email: str, request_ip: str | None = None) -> None:
    """
    Genera un token de reseteo (hash persistido) y envía email con el token *en claro*.
    Responde en silencio si el correo no existe para evitar enumeración.
    """
    email_norm = _norm_email(email)

    # Compatibilidad: busca por Email o NormalizedEmail si existiera
    email_col = _resolve_attr(User, "Email", "email")
    norm_email_col = _resolve_attr(User, "NormalizedEmail", "normalized_email")

    if not email_col and not norm_email_col:
        Log.error("Modelo User no define columnas de email (Email/NormalizedEmail). Abortando reset.")
        return

    q = db.query(User)
    if email_col and norm_email_col:
        q = q.filter(or_(email_col == email_norm, norm_email_col == email_norm.upper()))
    elif email_col:
        q = q.filter(email_col == email_norm)
    else:
        q = q.filter(norm_email_col == email_norm.upper())  # type: ignore[arg-type]

    user = q.first()
    if not user:
        # No revelar existencia del correo
        Log.info("Solicitud reset para email inexistente (silencioso). email=%s ip=%s", email_norm, request_ip)
        return

    # Generar token y persistir hash
    raw = secrets.token_urlsafe(32)
    token_hash = _sha256(raw)
    expires = datetime.utcnow() + timedelta(minutes=RESET_TTL_MINUTES)

    try:
        # Opcional: limpiar tokens vencidos del usuario para mantener higiene
        db.query(PasswordResetToken).filter(
            and_(
                PasswordResetToken.UserId == str(getattr(user, _resolve_name(User, "Id", "id"))),
                PasswordResetToken.ExpiresAt <= datetime.utcnow(),
            )
        ).delete(synchronize_session=False)

        prt = PasswordResetToken(
            UserId=str(getattr(user, _resolve_name(User, "Id", "id"))),
            TokenHash=token_hash,
            ExpiresAt=expires,
            Ip=request_ip,
        )
        db.add(prt)
        db.commit()

    except SQLAlchemyError as e:
        db.rollback()
        Log.exception("Error persistiendo token de reset para user=%s: %s", getattr(user, "Id", "?"), e)
        # No propagamos detalle para mantener simetría de respuesta
        return

    # Construir link (permite front configurable)
    sep = "&" if "?" in FRONTEND_RESET_URL else "?"
    reset_link = f"{FRONTEND_RESET_URL}{sep}token={raw}"

    try:
        send_password_reset_email(email_norm, reset_link)
    except Exception as e:  # pragma: no cover
        # No hacemos rollback del token por falla de mail; solo log
        Log.exception("Fallo enviando email de reset a %s: %s", email_norm, e)


def consume_reset_token(db: Session, token_raw: str, new_password: str) -> None:
    """
    Valida el token, cambia la contraseña y marca el token como usado.
    Lanza ValueError cuando el token no es válido/expiró o el usuario no existe.
    """
    token_hash = _sha256(token_raw)
    now = datetime.utcnow()

    prt = (
        db.query(PasswordResetToken)
        .filter(
            and_(
                PasswordResetToken.TokenHash == token_hash,
                PasswordResetToken.UsedAt.is_(None),
                PasswordResetToken.ExpiresAt > now,
            )
        )
        .order_by(PasswordResetToken.Id.desc())
        .first()
    )

    if not prt:
        raise ValueError("Token inválido o expirado")

    user_id_col = _resolve_attr(User, "Id", "id")
    if not user_id_col:
        raise ValueError("Modelo User no tiene columna Id")

    user = db.query(User).filter(user_id_col == prt.UserId).first()
    if not user:
        raise ValueError("Usuario no encontrado")

    # Campos de contraseña / security stamp
    pwd_col_name = _resolve_name(User, "PasswordHash", "hashed_password")
    if not pwd_col_name:
        raise ValueError("Modelo User no tiene PasswordHash/hashed_password")

    try:
        # Cambiar contraseña
        setattr(user, pwd_col_name, Hash.bcrypt(new_password))

        # Rotar SecurityStamp si existe (mejora de seguridad: invalida sesiones)
        if ROTATE_SECURITY_STAMP:
            sec_col = _resolve_name(User, "SecurityStamp", "security_stamp")
            if sec_col:
                setattr(user, sec_col, secrets.token_hex(16))

        # Marcar token como usado
        prt.UsedAt = now

        db.add_all([user, prt])
        db.commit()

    except SQLAlchemyError as e:
        db.rollback()
        Log.exception("Error aplicando reset password para user=%s: %s", getattr(user, "Id", "?"), e)
        raise ValueError("No fue posible restablecer la contraseña. Intente nuevamente.")
