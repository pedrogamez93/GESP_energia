import json
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from app.db.models.audit import AuditLog  # <-- ruta correcta

@event.listens_for(Session, "after_flush")
def audit_after_flush(session: Session, flush_context):
    meta = session.info.get("request_meta", {}) or {}
    actor = session.info.get("actor")  # {"id": "...", "username": "..."}

    def log(action: str, obj, changes: dict | None):
        if isinstance(obj, AuditLog):
            return
        session.add(AuditLog(
            action=action,
            resource_type=obj.__class__.__name__,
            resource_id=str(getattr(obj, "id", None)),
            http_method=meta.get("method"),
            path=meta.get("path"),
            status_code=meta.get("status_code"),
            actor_id=(actor or {}).get("id"),
            actor_username=(actor or {}).get("username"),
            session_id=meta.get("session_id"),
            request_id=meta.get("request_id"),
            ip=meta.get("ip"),
            user_agent=meta.get("user_agent"),
            changes_json=(json.dumps(changes) if changes else None),
            request_body_sha256=meta.get("request_body_sha256"),
            request_body_json=meta.get("request_body_json"),
        ))

    for obj in session.new:
        log("create", obj, None)

    for obj in session.deleted:
        log("delete", obj, None)

    for obj in session.dirty:
        state = inspect(obj)
        if not state.modified:
            continue
        changes = {}
        for attr in state.mapper.column_attrs:
            hist = state.attrs[attr.key].history
            if hist.has_changes():
                old = hist.deleted[0] if hist.deleted else None
                new = hist.added[0] if hist.added else getattr(obj, attr.key)
                if old != new:
                    changes[attr.key] = {"old": old, "new": new}
        if changes:
            log("update", obj, changes)
