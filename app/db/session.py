# app/db/session.py
from __future__ import annotations

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session as SASession

from app.core.config import settings
from app.audit.context import current_request_meta  # <-- contextvar con metadatos de request

# Flags por variables de entorno (opcionales)
READ_UNCOMMITTED = os.getenv("DB_READ_UNCOMMITTED", "1") == "1"
LOCK_TIMEOUT_MS  = int(os.getenv("DB_LOCK_TIMEOUT_MS", "5000"))

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,        # detecta conexiones muertas
    fast_executemany=True,     # mejora inserts masivos
    pool_recycle=1800,         # recicla conexiones viejas
    future=True,
)

@event.listens_for(engine, "connect")
def _set_session_pragmas(dbapi_connection, connection_record):
    """Aplica timeout y aislamiento en cada conexión (best-effort)."""
    try:
        cursor = dbapi_connection.cursor()
        if LOCK_TIMEOUT_MS and LOCK_TIMEOUT_MS > 0:
            cursor.execute(f"SET LOCK_TIMEOUT {LOCK_TIMEOUT_MS};")
        if READ_UNCOMMITTED:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
        cursor.close()
    except Exception:
        pass

class RequestAwareSession(SASession):
    """Session que hereda metadatos del request automáticamente (vía contextvar)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.info["request_meta"] = current_request_meta.get({})
        except Exception:
            self.info["request_meta"] = {}

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=RequestAwareSession,  # <-- clave: cualquier Session ve request_meta
)
