# app/api/v1/auth.py
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# 👈 usa el get_db que inyecta meta
from app.dependencies.db import get_db

from app.schemas.auth import TokenResponse
from app.services.auth_service import (
    login_and_issue_token,
    get_current_user,
)
from app.models.audit import AuditLog

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    token, user = login_and_issue_token(db, form.username, form.password)

    db.info["actor"] = {"id": str(getattr(user, "id", None)), "username": getattr(user, "username", None)}
    meta = getattr(request.state, "audit_meta", {}) or {}

    db.add(AuditLog(
        action="login",
        actor_id=str(getattr(user, "id", None)),
        actor_username=getattr(user, "username", None),
        ip=meta.get("ip"),
        user_agent=meta.get("user_agent"),
        http_method=meta.get("method") or "POST",
        path=meta.get("path") or str(request.url.path),
        status_code=status.HTTP_200_OK,
        request_id=meta.get("request_id"),
        # session_id=meta.get("session_id"),  # quita o implementa en el middleware
    ))
    db.commit()
    return TokenResponse(access_token=token, user=user)

@router.post("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db.info["actor"] = {"id": str(getattr(current_user, "id", None)), "username": getattr(current_user, "username", None)}
    meta = getattr(request.state, "audit_meta", {}) or {}

    db.add(AuditLog(
        action="logout",
        actor_id=str(getattr(current_user, "id", None)),
        actor_username=getattr(current_user, "username", None),
        ip=meta.get("ip"),
        user_agent=meta.get("user_agent"),
        http_method=meta.get("method") or "POST",
        path=meta.get("path") or str(request.url.path),
        status_code=status.HTTP_200_OK,
        request_id=meta.get("request_id"),
        # session_id=meta.get("session_id"),
    ))
    db.commit()
    return {"ok": True}
