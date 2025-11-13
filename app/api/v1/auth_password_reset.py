from __future__ import annotations
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth_password import ForgotPasswordIn, ResetPasswordIn
from app.services.password_reset_service import create_reset_token, consume_reset_token

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordIn, request: Request, db: Session = Depends(get_db)):
    # Siempre 200: evita enumeración de emails
    create_reset_token(db, payload.email, request.client.host if request.client else None)
    return {"detail": "Si el correo existe, enviaremos instrucciones para restablecer la contraseña."}

@router.post("/reset-password")
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)):
    consume_reset_token(db, payload.token, payload.new_password)
    return {"detail": "Contraseña restablecida correctamente."}
