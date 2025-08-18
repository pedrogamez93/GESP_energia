from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Annotated

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.identity import AspNetUser, AspNetRole
from app.schemas.auth import UserPublic

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Configuración de bloqueo (puedes mover a settings/.env si prefieres)
LOCKOUT_MAX_FAILED = 5
LOCKOUT_WINDOW_MINUTES = 15

def create_access_token(sub: str, roles: list[str], extra: dict | None = None, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": sub,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        **(extra or {}),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbDep = Annotated[Session, Depends(get_db)]

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbDep) -> UserPublic:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autorizado",
        headers={"WWW-Authenticate": "Bearer"},
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
