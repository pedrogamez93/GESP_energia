# app/audit/hooks.py
import json
import re
from typing import Any
from fastapi.encoders import jsonable_encoder
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from app.db.models.audit import AuditLog

ACTION_MAP = {
    "create": "crear",
    "update": "actualizar",
    "delete": "eliminar",
    "login": "ingreso",
    "logout": "salida",
}

# /.../xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx o números al final de la ruta
UUID_OR_ID_RE = re.compile(r"/([0-9a-fA-F-]{8,}|[0-9]+)(?:$|[/?#])")

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
        if isinstance(v, dict) and ("old" in v or "new" in v):
            out[k] = {"anterior": v.get("old"), "nuevo": v.get("new")}
        else:
            out[k] = v
    return out

def _resource_id_from_mapper(obj) -> list[str | None]:
    vals: list[str | None] = []
    try:
        state = inspect(obj)
        if state.identity:
            return [str(v) if v is not None else None for v in state.identity]
        if state.mapper is not None and state.mapper.primary_key:
            for col in state.mapper.primary_key:
                v = None
                if hasattr(obj, col.key):
                    v = getattr(obj, col.key)
                elif hasattr(obj, col.name):
                    v = getattr(obj, col.name)
                vals.append(None if v is None else str(v))
    except Exception:
        pass
    return vals

def _id_from_path(meta: dict) -> str | None:
    path = (meta or {}).get("path") or ""
    m = UUID_OR_ID_RE.search(path)
    return m.group(1) if m else None

def _compute_resource_id(obj, meta: dict) -> str | None:
    # 1) Identity / PK declaradas
    pk_vals = _resource_id_from_mapper(obj)
    if pk_vals and any(v is not None for v in pk_vals):
        return "|".join("NULL" if v is None else v for v in pk_vals)
    # 2) Nombres frecuentes
    for name in ("id", "Id", "ID", f"{obj.__class__.__name__}Id"):
        if hasattr(obj, name):
            val = getattr(obj, name)
            if val is not None:
                return str(val)
    # 3) Fallback desde la URL
    return _id_from_path(meta)

@event.listens_for(Session, "after_flush")
def audit_after_flush(session: Session, flush_context):
    meta = session.info.get("request_meta") or {}
    actor = session.info.get("actor") or {}

    def log(action: str, obj, changes: dict | None):
        if isinstance(obj, AuditLog):
            return
        try:
            changes_es = _spanish_changes(changes) if changes else None
            changes_json = _to_json_safe(changes_es) if changes_es else None

            rbj = meta.get("request_body_json")
            if isinstance(rbj, (dict, list)):
                rbj = _to_json_safe(rbj)

            session.add(
                AuditLog(
                    action=ACTION_MAP.get(action, action),
                    resource_type=obj.__class__.__name__,
                    resource_id=_compute_resource_id(obj, meta),
                    http_method=meta.get("method"),
                    path=meta.get("path"),
                    status_code=meta.get("status_code"),  # en main.py pon default=200 antes de call_next
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
        changes: dict[str, Any] = {}
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
