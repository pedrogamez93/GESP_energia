# app/db/session.py
from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session as SASession, Session

from app.core.config import settings
from app.audit.context import current_request_meta  # contextvar con metadatos del request

# Flags por variables de entorno (opcionales)
READ_UNCOMMITTED = os.getenv("DB_READ_UNCOMMITTED", "1") == "1"
LOCK_TIMEOUT_MS = int(os.getenv("DB_LOCK_TIMEOUT_MS", "5000"))

# -------------------------
# Pool tuning (IMPORTANTE)
# -------------------------
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))          # antes: default (5)
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "40"))    # antes: default (10)
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))    # segundos
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # segundos (30 min)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,           # detecta conexiones muertas antes de usarlas
    pool_recycle=POOL_RECYCLE,    # recicla conexiones viejas
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    fast_executemany=True,        # pyodbc: mejora inserts masivos
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
        # No mates la conexión por fallas de compatibilidad
        pass

class RequestAwareSession(SASession):
    """
    Session que hereda metadatos del request automáticamente (vía contextvar).
    Guardamos la REFERENCIA al dict para que luego pueda mutarse (status_code).
    """
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
    class_=RequestAwareSession,
)

def get_db() -> Generator[Session, None, None]:
    """
    Dependency de FastAPI.
    - Siempre cierra la sesión
    - Si hubo excepción, hace rollback para devolver la conexión limpia al pool
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        db.close()
