# app/utils/mail.py
from __future__ import annotations
import logging, smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)

# Config opcional (si no existe settings, el stub solo loguea)
try:
    from app.core.config import settings
except Exception:
    class _S:  # defaults: sin SMTP => solo log
        MAIL_FROM = None
        MAIL_SERVER = None
        MAIL_PORT = 587
        MAIL_USERNAME = None
        MAIL_PASSWORD = None
        MAIL_TLS = True
        MAIL_SSL = False
    settings = _S()

def send_password_reset_email(to_email: str, reset_link: str) -> None:
    """
    Si MAIL_* no está configurado, no falla: solo loguea el enlace.
    """
    if not getattr(settings, "MAIL_SERVER", None) or not getattr(settings, "MAIL_FROM", None):
        log.warning(
            "send_password_reset_email(): MAIL_* no configurado. NO se envía correo. "
            "to=%s link=%s", to_email, reset_link
        )
        return

    msg = EmailMessage()
    msg["Subject"] = "Restablecer contraseña"
    msg["From"] = settings.MAIL_FROM
    msg["To"] = to_email
    msg.set_content(
        f"Hola,\n\nPara restablecer tu contraseña haz clic en el siguiente enlace:\n{reset_link}\n\n"
        "Si no solicitaste este cambio, ignora este mensaje."
    )

    try:
        if getattr(settings, "MAIL_SSL", False):
            with smtplib.SMTP_SSL(settings.MAIL_SERVER, int(getattr(settings, "MAIL_PORT", 465))) as s:
                if getattr(settings, "MAIL_USERNAME", None):
                    s.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(settings.MAIL_SERVER, int(getattr(settings, "MAIL_PORT", 587))) as s:
                if getattr(settings, "MAIL_TLS", True):
                    s.starttls()
                if getattr(settings, "MAIL_USERNAME", None):
                    s.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                s.send_message(msg)
        log.info("Correo de reset enviado a %s", to_email)
    except Exception as e:
        log.exception("Fallo enviando correo de reset a %s: %s", to_email, e)
