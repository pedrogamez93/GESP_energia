# app/db/session.py
from __future__ import annotations

from typing import Generator
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# Flags por variables de entorno (opcionales; si no existen, no pasa nada raro)
READ_UNCOMMITTED = os.getenv("DB_READ_UNCOMMITTED", "1") == "1"   # por defecto ON
LOCK_TIMEOUT_MS  = int(os.getenv("DB_LOCK_TIMEOUT_MS", "5000"))   # por defecto 5000 ms

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,        # detecta conexiones muertas
    fast_executemany=True,     # mejora inserts masivos
    pool_recycle=1800,         # recicla conexiones viejas
    future=True,               # requerido por tu SQLAlchemy
)

@event.listens_for(engine, "connect")
def _set_session_pragmas(dbapi_connection, connection_record):
    """
    Aplica timeout y aislamiento de lectura liviana en CADA conexión.
    Envuelto en try/except para jamás tumbar la app si el driver no soporta los SET.
    """
    try:
        cursor = dbapi_connection.cursor()
        if LOCK_TIMEOUT_MS and LOCK_TIMEOUT_MS > 0:
            cursor.execute(f"SET LOCK_TIMEOUT {LOCK_TIMEOUT_MS};")
        if READ_UNCOMMITTED:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
        cursor.close()
    except Exception:
        # Si falla, seguimos con valores por defecto
        pass

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
