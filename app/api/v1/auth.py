
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt  # pip install "python-jose[cryptography]"

from app.dependencies.db import get_db  # 👈 usa el get_db que inyecta metadatos
from app.schemas.auth import TokenResponse
from app.services.auth_service import login_and_issue_token  # 👈 deja solo lo que existe
from app.models.audit import AuditLog
from app.core.config import settings  # Debe exponer SECRET_KEY y ALGORITHM

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

# 🧩 Token bearer para extraer el token del header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Decodifica el JWT y devuelve un objeto con id/username para auditoría.
    Si tienes otra estructura de claims, ajusta las keys (uid/user_id/sub/username).
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("uid") or payload.get("user_id") or payload.get("sub")
    username = payload.get("username") or payload.get("sub")
    if not (user_id or username):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    # Objeto simple con atributos .id y .username (compatible con tu código)
    from types import SimpleNamespace
    return SimpleNamespace(id=user_id, username=username)

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
    ))
    db.commit()
    return TokenResponse(access_token=token, user=user)

@router.post("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Si implementas revocación del token, llama aquí a revoke_current_token(request)
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
    ))
    db.commit()
    return {"ok": True}
