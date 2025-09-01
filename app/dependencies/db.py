# app/dependencies/db.py
from typing import Generator
from fastapi import Request
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

def get_db(request: Request) -> Generator[Session, None, None]:
    db = SessionLocal()
    # Copia segura: si no hay middleware, queda {}
    db.info["request_meta"] = getattr(request.state, "audit_meta", {}) or {}
    # Opcional: aquí puedes inyectar el actor autenticado en db.info["actor"]
    try:
        yield db
    finally:
        db.close()
