# app/dependencies/db.py
from typing import Generator, Optional
from fastapi import Request
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

def get_db(request: Optional[Request] = None) -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        meta = {}
        if request is not None:
            # copia segura: si el middleware no corrió, queda {}
            meta = getattr(request.state, "audit_meta", {}) or {}
        db.info["request_meta"] = getattr(request.state, "audit_meta", {}) or {}
        yield db
    finally:
        db.close()
