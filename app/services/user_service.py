from __future__ import annotations

import logging
from typing import Optional, Literal, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc, desc, or_

from app.schemas.user import UserCreate, UserUpdate, UserPatch
from app.db.models.user import User  # alias de AspNetUser
from app.utils.hash import Hash

Log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers: resolución dinámica de nombres
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_attr(cls, *names):
    for name in names:
        if hasattr(cls, name):
            return getattr(cls, name)
    return None

def _resolve_name(cls, *names) -> Optional[str]:
    for name in names:
        if hasattr(cls, name):
            return name
    return None

def _split_full_name(full_name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not full_name:
        return None, None
    s = full_name.strip()
    if not s:
        return None, None
    parts = s.split()
    if len(parts) == 1:
        return parts[0], None
    # Heurística: todo salvo última palabra = nombres; última palabra = apellido principal
    return " ".join(parts[:-1]), parts[-1]

def _apply_name_fields(payload: dict, full_name: Optional[str]):
    """
    Si el modelo no tiene FullName, pero tiene Nombres/Apellidos, deriva desde full_name si no fueron provistos.
    """
    has_full_name = _resolve_name(User, "FullName", "full_name") is not None
    has_nombres = _resolve_name(User, "Nombres", "nombres") is not None
    has_apellidos = _resolve_name(User, "Apellidos", "apellidos") is not None

    if has_full_name:
        # Si existe FullName en el modelo, úsalo si viene
        if full_name is not None:
            payload[_resolve_name(User, "FullName", "full_name")] = full_name
        return

    # Si no hay FullName, intenta escribir Nombres/Apellidos
    if (has_nombres or has_apellidos) and full_name:
        nom, ape = _split_full_name(full_name)
        if has_nombres and nom and "Nombres" not in payload and "nombres" not in payload:
            payload[_resolve_name(User, "Nombres", "nombres")] = nom
        if has_apellidos and ape and "Apellidos" not in payload and "apellidos" not in payload:
            payload[_resolve_name(User, "Apellidos", "apellidos")] = ape

# ─────────────────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_user(db: Session, data: UserCreate):
    email_field    = _resolve_name(User, "Email", "email")
    password_field = _resolve_name(User, "PasswordHash", "hashed_password")
    if not (email_field and password_field):
        raise RuntimeError("Modelo User no define Email/PasswordHash.")

    payload: dict = {email_field: data.email.strip().lower(),
                     password_field: Hash.bcrypt(data.password)}

    # Cargar extras si el modelo los tiene
    def put_if_model_has(field_name: str, value):
        if value is None:
            return
        model_name = _resolve_name(User, field_name, field_name[:1].lower()+field_name[1:])
        if model_name:
            payload[model_name] = value

    # Nombre compuesto o Nombres/Apellidos explícitos
    _apply_name_fields(payload, data.full_name)
    put_if_model_has("Nombres", data.Nombres)
    put_if_model_has("Apellidos", data.Apellidos)

    put_if_model_has("PhoneNumber", data.PhoneNumber)
    put_if_model_has("NumeroTelefonoOpcional", data.NumeroTelefonoOpcional)
    put_if_model_has("Address", data.Address)
    put_if_model_has("City", data.City)
    put_if_model_has("PostalCode", data.PostalCode)
    put_if_model_has("Cargo", data.Cargo)
    put_if_model_has("Nacionalidad", data.Nacionalidad)
    put_if_model_has("Rut", data.Rut)
    put_if_model_has("ComunaId", data.ComunaId)
    put_if_model_has("SexoId", data.SexoId)
    put_if_model_has("Certificado", data.Certificado)
    put_if_model_has("Validado", data.Validado)
    put_if_model_has("Active", True if data.Active is None else data.Active)

    user = User(**payload)
    db.add(user)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # Colisión de email u otra restricción
        raise ValueError("No se pudo crear el usuario (posible email duplicado).") from e

    db.refresh(user)
    return user

def get_user_by_id(db: Session, user_id: Union[int, str]) -> Optional[User]:
    key = _resolve_attr(User, "Id", "id")
    if key is None:
        return None
    return db.query(User).filter(key == user_id).first()

def update_user(db: Session, user_id: Union[int, str], data: UserUpdate) -> User:
    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError("Usuario no encontrado.")

    # Campos permitidos a actualizar (no email ni password aquí)
    payload: dict = {}
    def put_if_model_has(field_name: str, value):
        if value is None:
            return
        model_name = _resolve_name(User, field_name, field_name[:1].lower()+field_name[1:])
        if model_name:
            payload[model_name] = value

    _apply_name_fields(payload, data.full_name)
    put_if_model_has("Nombres", data.Nombres)
    put_if_model_has("Apellidos", data.Apellidos)
    put_if_model_has("PhoneNumber", data.PhoneNumber)
    put_if_model_has("NumeroTelefonoOpcional", data.NumeroTelefonoOpcional)
    put_if_model_has("Address", data.Address)
    put_if_model_has("City", data.City)
    put_if_model_has("PostalCode", data.PostalCode)
    put_if_model_has("Cargo", data.Cargo)
    put_if_model_has("Nacionalidad", data.Nacionalidad)
    put_if_model_has("Rut", data.Rut)
    put_if_model_has("ComunaId", data.ComunaId)
    put_if_model_has("SexoId", data.SexoId)
    put_if_model_has("Certificado", data.Certificado)
    put_if_model_has("Validado", data.Validado)
    if data.Active is not None:
        put_if_model_has("Active", data.Active)

    for k, v in payload.items():
        setattr(user, k, v)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def patch_user(db: Session, user_id: Union[int, str], data: UserPatch) -> User:
    # Misma lógica que update (PATCH parcial)
    return update_user(db, user_id, data)

def change_password(db: Session, user_id: Union[int, str], new_password: str) -> User:
    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError("Usuario no encontrado.")

    password_field = _resolve_name(User, "PasswordHash", "hashed_password")
    if not password_field:
        raise RuntimeError("Modelo User no define PasswordHash.")

    setattr(user, password_field, Hash.bcrypt(new_password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def soft_delete_user(db: Session, user_id: Union[int, str]) -> User:
    """Soft delete = Active = False (si la columna existe)."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError("Usuario no encontrado.")

    active_field = _resolve_name(User, "Active", "active")
    if not active_field:
        raise RuntimeError("Modelo User no tiene columna Active para soft delete.")

    setattr(user, active_field, False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def toggle_active_user(db: Session, user_id: Union[int, str], enable: bool) -> User:
    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError("Usuario no encontrado.")
    active_field = _resolve_name(User, "Active", "active")
    if not active_field:
        raise RuntimeError("Modelo User no tiene columna Active.")

    setattr(user, active_field, enable)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "Id",
    sort_dir: str = "asc",
    status: Literal["active", "inactive", "all"] = "active",
):
    """Listado MSSQL-friendly con filtro por Active (tratando NULL como activo para compatibilidad)."""
    id_col        = _resolve_attr(User, "Id", "id")
    email_col     = _resolve_attr(User, "Email", "email")
    full_name_col = _resolve_attr(User, "FullName", "full_name")
    created_col   = _resolve_attr(User, "CreatedAt", "created_at", "Created", "createdAt")

    allowed_cols = {
        "Id": id_col, "id": id_col,
        "Email": email_col, "email": email_col,
        "FullName": full_name_col, "full_name": full_name_col,
        "CreatedAt": created_col, "created_at": created_col,
    }

    default_col = id_col or email_col
    col = allowed_cols.get(sort_by, default_col) or default_col
    order_expr = asc(col) if str(sort_dir).lower() == "asc" else desc(col)

    q = db.query(User)

    if hasattr(User, "Active"):
        active_col = getattr(User, "Active")
        if status == "active":
            q = q.filter(or_(active_col == True, active_col.is_(None)))
        elif status == "inactive":
            q = q.filter(active_col == False)

    return q.order_by(order_expr).offset(skip).limit(limit).all()
