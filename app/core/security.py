# app/core/security.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Iterable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.identity import AspNetUser, AspNetRole  # 👈 asegúrate que exista AspNetRole
from app.schemas.auth import UserPublic
from app.utils.identity_password import verify_aspnet_password
from app.core.roles import ADMIN, ADMIN_VARIANTS

# ─────────────────────────────────────────────────────────────
# ✅ Compatibilidad con auth_service
LOCKOUT_MAX_FAILED = 5
LOCKOUT_WINDOW_MINUTES = 15
# ─────────────────────────────────────────────────────────────

ROLE_ADMIN = "ADMINISTRADOR"
ROLE_GESTOR_UNIDAD = "GESTOR_UNIDAD"


# ─────────────────────────────────────────────────────────────
# JWT helpers
# ─────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────
# DB dep
# ─────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


# ─────────────────────────────────────────────────────────────
# Roles helpers
# ─────────────────────────────────────────────────────────────
def _is_guid(s: str) -> bool:
    # GUID típico: 8-4-4-4-12
    if not s:
        return False
    t = s.strip()
    if len(t) != 36:
        return False
    parts = t.split("-")
    if len(parts) != 5:
        return False
    return [len(p) for p in parts] == [8, 4, 4, 4, 12]


def _normalize_role(name: str | None) -> str | None:
    if not name:
        return None
    up = name.strip().upper()

    # admin variants -> ADMINISTRADOR
    if up in {r.upper() for r in ADMIN_VARIANTS}:
        return ADMIN  # "ADMINISTRADOR"

    # normalización extra (por si viene raro)
    if up in {"GESTOR UNIDAD", "GESTOR-DE-UNIDAD", "GESTOR_UNIDAD"}:
        return ROLE_GESTOR_UNIDAD

    return up


def _merge_roles(*groups: Iterable[str]) -> list[str]:
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


def _role_ids_to_names(db: Session, role_ids: list[str]) -> list[str]:
    """
    Convierte RoleId GUID -> NormalizedName/Name consultando AspNetRoles.
    """
    ids = [x.strip() for x in (role_ids or []) if x and _is_guid(x)]
    if not ids:
        return []

    rows = (
        db.query(AspNetRole)
        .filter(AspNetRole.Id.in_(ids))
        .all()
    )
    names: list[str] = []
    for r in rows:
        nm = getattr(r, "NormalizedName", None) or getattr(r, "Name", None) or ""
        nm = nm.strip()
        if nm:
            names.append(nm)
    return names


# ─────────────────────────────────────────────────────────────
# Bearer extractor con errores detallados
# ─────────────────────────────────────────────────────────────
def _raise_401(msg: str, err: str | None = None, desc: str | None = None) -> None:
    hdr = "Bearer"
    if err:
        hdr = f'Bearer error="{err}"' if not desc else f'Bearer error="{err}", error_description="{desc}"'
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=msg,
        headers={"WWW-Authenticate": hdr},
    )


def bearer_token_required(request: Request) -> str:
    authorization: str | None = request.headers.get("authorization")
    scheme, param = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer" or not param:
        _raise_401(
            "Falta token de autorización",
            "invalid_request",
            "Header Authorization: Bearer <token> es requerido",
        )
    return param.strip()


# ─────────────────────────────────────────────────────────────
# Current user / Roles
# ─────────────────────────────────────────────────────────────
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

    user = db.query(AspNetUser).filter(AspNetUser.Id == sub).first()
    if not user:
        _raise_401("Usuario no encontrado", "invalid_token", "El 'sub' del token no corresponde a un usuario válido")

    # 1) Roles desde token: pueden venir como NOMBRES o como RoleId GUID
    token_role_names = [r for r in roles_from_token if r and not _is_guid(str(r))]
    token_role_ids = [str(r) for r in roles_from_token if r and _is_guid(str(r))]
    token_role_names_from_ids = _role_ids_to_names(db, token_role_ids)

    # 2) Roles desde DB: si tu relationship user.roles está bien, esto ya trae names
    roles_db_raw = [
        (getattr(r, "NormalizedName", None) or getattr(r, "Name", None) or "")
        for r in (getattr(user, "roles", None) or [])
    ]

    roles_final = _merge_roles(token_role_names, token_role_names_from_ids, roles_db_raw)

    return UserPublic(
        id=str(user.Id),
        username=user.UserName,
        email=user.Email,
        nombres=user.Nombres,
        apellidos=user.Apellidos,
        roles=roles_final,
    )


def require_roles(*required: str):
    # "*" = cualquier usuario autenticado
    if len(required) == 1 and required[0] == "*":
        def _dep_any(user: Annotated[UserPublic, Depends(get_current_user)]):
            return user
        return _dep_any

    required_norm = {_normalize_role(r) for r in required if _normalize_role(r)}

    def _dep(user: Annotated[UserPublic, Depends(get_current_user)]):
        user_roles = {_normalize_role(r) for r in (user.roles or []) if _normalize_role(r)}
        if required_norm and required_norm.isdisjoint(user_roles):
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


def require_admin_or_gestor_unidad():
    """
    Permite acciones operativas a ADMINISTRADOR o GESTOR_UNIDAD.
    """
    return require_roles(ROLE_ADMIN, ROLE_GESTOR_UNIDAD)


# ─────────────────────────────────────────────────────────────
# Password helpers
# ─────────────────────────────────────────────────────────────
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
    if stored_hash.startswith("$2"):
        try:
            return _ctx().verify(plain_password, stored_hash)
        except Exception:
            pass
    return verify_aspnet_password(stored_hash, plain_password)


def hash_password(plain_password: str) -> str:
    return _ctx().hash(plain_password)
