# app/audit/hooks.py
import json
from typing import Any
from fastapi.encoders import jsonable_encoder
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from app.db.models.audit import AuditLog  # ruta correcta

ACTION_MAP = {
    "create": "crear",
    "update": "actualizar",
    "delete": "eliminar",
    "login": "ingreso",
    "logout": "salida",
}

def _to_json_safe(value: Any) -> str:
    try:
        enc = jsonable_encoder(value)
        return json.dumps(enc, ensure_ascii=False)
    except Exception:
        try:
            return json.dumps(str(value), ensure_ascii=False)
        except Exception:
            return '""'

def _spanish_changes(changes: dict[str, Any]) -> dict[str, Any]:
    """Convierte {"old": x, "new": y} -> {"anterior": x, "nuevo": y}."""
    out: dict[str, Any] = {}
    for k, v in (changes or {}).items():
        if isinstance(v, dict) and "old" in v or "new" in v:
            out[k] = {"anterior": v.get("old"), "nuevo": v.get("new")}
        else:
            out[k] = v
    return out

def _get_resource_id(obj) -> str | None:
    """
    Obtiene la PK aunque no se llame 'id'. Soporta PK compuesta.
    1) usa state.identity (si ya está),
    2) si no, lee columnas PK del mapper,
    3) fallback a nombres comunes.
    """
    try:
        state = inspect(obj)
        # 1) Identity si ya existe (tras flush en inserts o siempre en updates)
        if state.identity:
            return "|".join(str(v) for v in state.identity if v is not None)
        # 2) PKs desde el mapper (útil si identity aún no está poblado)
        if state.mapper is not None and state.mapper.primary_key:
            pks = []
            for col in state.mapper.primary_key:
                try:
                    pks.append(getattr(obj, col.key))
                except Exception:
                    pks.append(None)
            if any(v is not None for v in pks):
                return "|".join("NULL" if v is None else str(v) for v in pks)
        # 3) Fallback por nombres típicos
        for name in ("id", "Id", "ID", f"{obj.__class__.__name__}Id"):
            if hasattr(obj, name):
                val = getattr(obj, name)
                return None if val is None else str(val)
    except Exception:
        pass
    return None

@event.listens_for(Session, "after_flush")
def audit_after_flush(session: Session, flush_context):
    meta = session.info.get("request_meta") or {}
    actor = session.info.get("actor") or {}

    def log(action: str, obj, changes: dict | None):
        if isinstance(obj, AuditLog):
            return
        try:
            # españoliza cambios
            changes_es = _spanish_changes(changes) if changes else None
            changes_json = _to_json_safe(changes_es) if changes_es else None

            rbj = meta.get("request_body_json")
            if isinstance(rbj, (dict, list)):
                rbj = _to_json_safe(rbj)

            session.add(
                AuditLog(
                    action=ACTION_MAP.get(action, action),
                    resource_type=obj.__class__.__name__,   # traduce con un map si quieres
                    resource_id=_get_resource_id(obj),
                    http_method=meta.get("method"),
                    path=meta.get("path"),
                    status_code=meta.get("status_code"),    # puede ser None (ver nota abajo)
                    actor_id=actor.get("id"),
                    actor_username=actor.get("username"),
                    session_id=meta.get("session_id"),
                    request_id=meta.get("request_id"),
                    ip=meta.get("ip"),
                    user_agent=meta.get("user_agent"),
                    changes_json=changes_json,
                    request_body_sha256=meta.get("request_body_sha256"),
                    request_body_json=rbj,
                )
            )
        except Exception as e:
            session.info["audit_error"] = f"{type(e).__name__}: {e}"

    # crear
    for obj in session.new:
        log("create", obj, None)

    # eliminar
    for obj in session.deleted:
        log("delete", obj, None)

    # actualizar
    for obj in session.dirty:
        state = inspect(obj)
        if not state.modified:
            continue
        changes = {}
        for attr in state.mapper.column_attrs:
            hist = state.attrs[attr.key].history
            if not hist.has_changes():
                continue
            old = hist.deleted[0] if hist.deleted else None
            new = hist.added[0] if hist.added else getattr(obj, attr.key)
            if old != new:
                changes[attr.key] = {"old": old, "new": new}
        if changes:
            log("update", obj, changes)
