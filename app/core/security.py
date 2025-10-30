# app/core/security.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional, Iterable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.identity import AspNetUser
from app.schemas.auth import UserPublic
from app.utils.identity_password import verify_aspnet_password
from app.core.roles import ADMIN, ADMIN_VARIANTS  # para mapear variantes

# ───────────────────────────────────────────────────────────────────────────────
# JWT helpers
# ───────────────────────────────────────────────────────────────────────────────

def create_access_token(
    sub: str,
    roles: list[str],
    extra: dict | None = None,
    expires_minutes: int | None = None,
) -> str:
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

# ───────────────────────────────────────────────────────────────────────────────
# DB dep
# ───────────────────────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbDep = Annotated[Session, Depends(get_db)]

# ───────────────────────────────────────────────────────────────────────────────
# Roles helpers
# ───────────────────────────────────────────────────────────────────────────────

def _normalize_role(name: str | None) -> str | None:
    """
    Normaliza nombres de rol a MAYÚSCULAS y corrige variantes conocidas.
    - Mapea cualquier variante en ADMIN_VARIANTS -> ADMIN
    """
    if not name:
        return None
    up = name.strip().upper()
    if up in {r.upper() for r in ADMIN_VARIANTS}:
        return ADMIN  # "ADMINISTRADOR"
    return up

def _merge_roles(*groups: Iterable[str]) -> list[str]:
    """
    Une, normaliza y deduplica roles.
    """
    seen = set()
    out: list[str] = []
    for g in groups:
        for r in (g or []):
            nr = _normalize_role(r)
            if not nr:
                continue
            if nr not in seen:
                seen.add(nr)
                out.append(nr)
    return out

# ───────────────────────────────────────────────────────────────────────────────
# Bearer extractor con errores detallados
# ───────────────────────────────────────────────────────────────────────────────

def _raise_401(msg: str, err: str | None = None, desc: str | None = None) -> None:
    hdr = 'Bearer'
    if err:
        if desc:
            hdr = f'Bearer error="{err}", error_description="{desc}"'
        else:
            hdr = f'Bearer error="{err}"'
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=msg,
        headers={"WWW-Authenticate": hdr},
    )

def bearer_token_required(request: Request) -> str:
    """
    Extrae y valida el esquema Bearer. Lanza 401 con motivo claro si falta.
    """
    authorization: str | None = request.headers.get("authorization")
    scheme, param = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer" or not param:
        _raise_401(
            "Falta token de autorización",
            "invalid_request",
            "Header Authorization: Bearer <token> es requerido",
        )
    return param.strip()

# ───────────────────────────────────────────────────────────────────────────────
# Current user / Roles
# ───────────────────────────────────────────────────────────────────────────────

def get_current_user(token: Annotated[str, Depends(bearer_token_required)], db: DbDep) -> UserPublic:
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        _raise_401("Token expirado", "invalid_token", "El claim 'exp' ya caducó")
    except JWTError as e:
        _raise_401("Token inválido", "invalid_token", str(e))

    sub: str | None = payload.get("sub")
    roles_from_token = payload.get("roles") or []
    if not sub:
        _raise_401("Token inválido: falta 'sub'", "invalid_token", "El token no contiene el subject (sub)")

    # Busca usuario; si no existe, también 401 (credenciales no válidas)
    user = db.query(AspNetUser).filter(AspNetUser.Id == sub).first()
    if not user:
        _raise_401("Usuario no encontrado", "invalid_token", "El 'sub' del token no corresponde a un usuario válido")

    # Combina roles del token + BD (normalizados)
    roles_db_raw = [
        (getattr(r, "NormalizedName", None) or getattr(r, "Name", None) or "")
        for r in (user.roles or [])
    ]
    roles_final = _merge_roles(roles_from_token, roles_db_raw)

    return UserPublic(
        id=str(user.Id),
        username=user.UserName,
        email=user.Email,
        nombres=user.Nombres,
        apellidos=user.Apellidos,
        roles=roles_final,
    )

def require_roles(*required: str):
    """
    - '*'  => solo autenticado (sin chequear rol)
    - Si se pasan roles, se normalizan (corrige variantes de ADMIN)
    """
    if len(required) == 1 and required[0] == "*":
        def _dep_any(user: Annotated[UserPublic, Depends(get_current_user)]):
            return user
        return _dep_any

    required_norm = {_normalize_role(r) for r in required if _normalize_role(r)}

    def _dep(user: Annotated[UserPublic, Depends(get_current_user)]):
        user_roles = {_normalize_role(r) for r in (user.roles or []) if _normalize_role(r)}
        if required_norm and required_norm.isdisjoint(user_roles):
            # 403 con detalle explícito
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "forbidden",
                    "msg": "Rol insuficiente",
                    "required": sorted(r for r in required_norm if r),
                    "user_roles": sorted(r for r in user_roles if r),
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    return _dep

# ───────────────────────────────────────────────────────────────────────────────
# Password helpers (bcrypt/ASP.NET)
# ───────────────────────────────────────────────────────────────────────────────

_pwd_ctx = None  # CryptContext perezoso

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
