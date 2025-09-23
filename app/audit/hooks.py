import json
from typing import Any
from fastapi.encoders import jsonable_encoder
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from app.db.models.audit import AuditLog  # ruta correcta

def _to_json_safe(value: Any) -> str:
    try:
        enc = jsonable_encoder(value)
        return json.dumps(enc, ensure_ascii=False)
    except Exception:
        try:
            return json.dumps(str(value), ensure_ascii=False)
        except Exception:
            return '""'

def _get_resource_id(obj) -> str | None:
    """Obtiene la PK aunque no se llame 'id'. Soporta PK compuesta."""
    try:
        state = inspect(obj)
        if state.identity:
            return "|".join(str(v) for v in state.identity if v is not None)
        # fallback: nombres típicos
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
            changes_json = _to_json_safe(changes) if changes else None
            rbj = meta.get("request_body_json")
            if isinstance(rbj, (dict, list)):
                rbj = _to_json_safe(rbj)

            session.add(
                AuditLog(
                    action=action,
                    resource_type=obj.__class__.__name__,
                    resource_id=_get_resource_id(obj),
                    http_method=meta.get("method"),
                    path=meta.get("path"),
                    status_code=meta.get("status_code"),
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

    # create
    for obj in session.new:
        log("create", obj, None)

    # delete
    for obj in session.deleted:
        log("delete", obj, None)

    # update
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
