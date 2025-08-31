# @router.post("/login", response_model=TokenResponse)
# def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
#     token, user = login_and_issue_token(db, form.username, form.password)
#     return TokenResponse(access_token=token, user=user)

# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import authenticate, issue_jwt, revoke_current_token, get_current_user
from app.models.audit import AuditLog  # Asegúrate de tener este modelo
from app.schemas.auth import LoginForm, TokenResponse  # o usa OAuth2PasswordRequestForm si así lo tienes

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
def login(
    form: LoginForm,
    request: Request,
    db: Session = Depends(get_db),
):
    user = authenticate(form.username, form.password, db)
    if not user:
        # Opcional: registrar intento fallido
        meta = getattr(request.state, "audit_meta", {}) or {}
        db.add(AuditLog(
            action="login_failed",
            actor_id=None, actor_username=form.username,
            ip=meta.get("ip"), user_agent=meta.get("user_agent"),
            http_method=meta.get("method", "POST"), path=meta.get("path", "/auth/login"),
            status_code=status.HTTP_401_UNAUTHORIZED,
        ))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token, jti = issue_jwt(user, db=db)  # si tu issue_jwt necesita db para persistir jti
    meta = getattr(request.state, "audit_meta", {}) or {}

    db.add(AuditLog(
        action="login",
        actor_id=str(user.id), actor_username=user.username,
        ip=meta.get("ip"), user_agent=meta.get("user_agent"),
        http_method=meta.get("method", "POST"), path=meta.get("path", "/auth/login"),
        status_code=status.HTTP_200_OK,
        extra={"jti": jti}  # opcional
    ))
    db.commit()

    return {"access_token": token, "token_type": "bearer"}

@router.post("/logout")
def logout(
    request: Request,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Revoca el token actual (e.g., a través del jti en la blacklist)
    revoke_current_token(request, db=db)

    meta = getattr(request.state, "audit_meta", {}) or {}
    db.add(AuditLog(
        action="logout",
        actor_id=str(current.id), actor_username=current.username,
        ip=meta.get("ip"), user_agent=meta.get("user_agent"),
        http_method=meta.get("method", "POST"), path=meta.get("path", "/auth/logout"),
        status_code=status.HTTP_200_OK,
    ))
    db.commit()
    return {"ok": True}
