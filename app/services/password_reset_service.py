from __future__ import annotations
from datetime import datetime, timedelta
import secrets, hashlib
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models.user import User
from app.db.models.password_reset import PasswordResetToken
from app.utils.hash import Hash  # ya usas bcrypt aquí para passwords
# dejas un stub para enviar correo
from app.utils.mail import send_password_reset_email  # implementa tu SMTP

RESET_TTL_MINUTES = 30

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def create_reset_token(db: Session, email: str, request_ip: str | None = None) -> None:
    # No revelar si existe o no el usuario
    user = db.query(User).filter(getattr(User, "Email") == email.lower()).first()
    if not user:
        return

    # Genera token y guarda el hash
    raw = secrets.token_urlsafe(32)
    token_hash = _sha256(raw)
    expires = datetime.utcnow() + timedelta(minutes=RESET_TTL_MINUTES)

    prt = PasswordResetToken(UserId=str(getattr(user, "Id")), TokenHash=token_hash, ExpiresAt=expires, Ip=request_ip)
    db.add(prt)
    db.commit()

    # Envía el correo con el token en plano
    reset_link = f"https://tu-frontend/reset-password?token={raw}"
    send_password_reset_email(email, reset_link)

def consume_reset_token(db: Session, token_raw: str, new_password: str) -> None:
    token_hash = _sha256(token_raw)
    now = datetime.utcnow()

    prt = db.query(PasswordResetToken).filter(
        and_(
            PasswordResetToken.TokenHash == token_hash,
            PasswordResetToken.UsedAt.is_(None),
            PasswordResetToken.ExpiresAt > now,
        )
    ).order_by(PasswordResetToken.Id.desc()).first()

    if not prt:
        raise ValueError("Token inválido o expirado")

    user = db.query(User).filter(getattr(User, "Id") == prt.UserId).first()
    if not user:
        raise ValueError("Usuario no encontrado")

    # Cambia la contraseña
    setattr(user, "PasswordHash", Hash.bcrypt(new_password))
    prt.UsedAt = now
    db.add_all([user, prt])
    db.commit()
