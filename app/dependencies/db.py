# app/dependencies/db.py
from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

def get_db() -> Generator[Session, None, None]:
    """
    Devuelve una Session que ya viene con info['request_meta']
    (inyectada por RequestAwareSession vía contextvar).
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
