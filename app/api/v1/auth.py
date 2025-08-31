# app/api/v1/auth.py
from typing import Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.core.security import authenticate, issue_jwt, revoke_current_token, get_current_user
from app.models.audit import AuditLog

router = APIRouter(prefix="/auth", tags=["Auth"])

class LoginJSON(BaseModel):
    username: str
    password: str

async def extract_credentials(
    request: Request,
    body: Optional[LoginJSON] = Body(default=None),
) -> Tuple[str, str]:
    # Si viene JSON válido, úsalo
    if body is not None:
        return body.username, body.password

    # Si no, intenta como form (application/x-www-form-urlencoded o multipart/form-data)
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    if not username or not password:
        # Emula el formato típico de error de validación de FastAPI
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {"loc": ["body", "username"], "msg": "field required", "type": "value_error.missing"},
                {"loc": ["body", "password"], "msg": "field required", "type": "value_error.missing"},
            ],
        )
    return username, password

@router.post("/login")
async def login(
    request: Request,
    creds: Tuple[str, str] = Depends(extract_credentials),
    db: Session = Depends(get_db),
):
    username, password = creds
    user = authenticate(username, password, db)
    if not user:
        meta = getattr(request.state, "audit_meta", {}) or {}
        db.add(AuditLog(
            action="login_failed",
            actor_id=None, actor_username=username,
            ip=meta.get("ip"), user_agent=meta.get("user_agent"),
            http_method=meta.get("method", "POST"), path=meta.get("path", "/auth/login"),
            status_code=status.HTTP_401_UNAUTHORIZED,
        ))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token, jti = issue_jwt(user, db=db)
    meta = getattr(request.state, "audit_meta", {}) or {}
    db.add(AuditLog(
        action="login",
        actor_id=str(user.id), actor_username=user.username,
        ip=meta.get("ip"), user_agent=meta.get("user_agent"),
        http_method=meta.get("method", "POST"), path=meta.get("path", "/auth/login"),
        status_code=status.HTTP_200_OK,
        extra={"jti": jti},
    ))
    db.commit()
    return {"access_token": token, "token_type": "bearer"}

@router.post("/logout")
async def logout(
    request: Request,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
