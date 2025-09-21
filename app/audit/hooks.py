import json
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.db.models.audit import AuditLog  # ruta correcta


def _to_json_safe(value: Any) -> str:
    """
    Convierte dict/list/obj a JSON serializable:
      - datetime/date -> ISO 8601
      - UUID -> str
      - Decimal -> float (o str según encoder por defecto)
      - Objetos ORM -> dict básico si aplica
    Nunca lanza excepción (fallback a str(value)).
    """
    try:
        enc = jsonable_encoder(value)  # maneja datetime/uuid/decimal, etc.
        return json.dumps(enc, ensure_ascii=False)
    except Exception:
        try:
            return json.dumps(str(value), ensure_ascii=False)
        except Exception:
            return '""'


@event.listens_for(Session, "after_flush")
def audit_after_flush(session: Session, flush_context):
    # Metadatos inyectados por middleware o endpoint (si existen)
    meta = session.info.get("request_meta") or {}
    actor = session.info.get("actor") or {}  # {"id": "...", "username": "..."}

    def log(action: str, obj, changes: dict | None):
        # Evita auditar la propia tabla de auditoría
        if isinstance(obj, AuditLog):
            return

        try:
            # Serializa los "changes" de manera segura
            changes_json = _to_json_safe(changes) if changes else None

            # Serializa body (si viene como dict/list). Si ya es str, lo respetamos.
            rbj = meta.get("request_body_json")
            if isinstance(rbj, (dict, list)):
                rbj = _to_json_safe(rbj)

            session.add(
                AuditLog(
                    action=action,
                    resource_type=obj.__class__.__name__,
                    # si tu PK no es 'id', ajusta aquí
                    resource_id=str(getattr(obj, "id", None)),
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
            # La auditoría JAMÁS debe romper la transacción principal
            # Guardamos el error en session.info para inspección si hace falta.
            session.info["audit_error"] = f"{type(e).__name__}: {e}"

    # Altas
    for obj in session.new:
        log("create", obj, None)

    # Bajas
    for obj in session.deleted:
        log("delete", obj, None)

    # Modificaciones
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
            # Preferimos el valor agregado; si no, el actual del objeto
            new = hist.added[0] if hist.added else getattr(obj, attr.key)

            # Evita ruido si SQLA considera cambio sin diferencia real
            if old != new:
                changes[attr.key] = {"old": old, "new": new}

        if changes:
            log("update", obj, changes)
