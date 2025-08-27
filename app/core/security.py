# app/core/security.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.identity import AspNetUser
from app.schemas.auth import UserPublic
from app.utils.identity_password import verify_aspnet_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

LOCKOUT_MAX_FAILED = 5
LOCKOUT_WINDOW_MINUTES = 15

# -------- JWT --------

def create_access_token(sub: str, roles: list[str], extra: dict | None = None, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": sub, "roles": roles, "iat": int(now.timestamp()), "exp": int(exp.timestamp()), **(extra or {})}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

# -------- DB dep --------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbDep = Annotated[Session, Depends(get_db)]

# -------- Current user / Roles --------

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbDep) -> UserPublic:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado", headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = decode_token(token)
        sub: str | None = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(AspNetUser).filter(AspNetUser.Id == sub).first()
    if not user:
        raise credentials_exception

    roles = [r.NormalizedName or r.Name or "" for r in (user.roles or [])]
    return UserPublic(
        id=str(user.Id),
        username=user.UserName,
        email=user.Email,
        nombres=user.Nombres,
        apellidos=user.Apellidos,
        roles=[r for r in roles if r],
    )

def require_roles(*required: str):
    required_norm = {r.upper() for r in required}
    def _dep(user: Annotated[UserPublic, Depends(get_current_user)]):
        user_roles = {r.upper() for r in user.roles}
        if required_norm and required_norm.isdisjoint(user_roles):
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return user
    return _dep

# -------- Password helpers (lazy bcrypt) --------

_pwd_ctx = None  # CryptContext se inicializa perezosamente

def _ctx():
    global _pwd_ctx
    if _pwd_ctx is None:
        from passlib.context import CryptContext
        _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return _pwd_ctx

def verify_password_any(plain_password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    # bcrypt local
    if stored_hash.startswith("$2"):
        try:
            return _ctx().verify(plain_password, stored_hash)
        except Exception:
            pass
    # ASP.NET Identity v2/v3
    return verify_aspnet_password(stored_hash, plain_password)

def hash_password(plain_password: str) -> str:
    return _ctx().hash(plain_password)
