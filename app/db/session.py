# app/db/session.py
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Recomendado para SQL Server con pyodbc:
# settings.DATABASE_URL => "mssql+pyodbc://USER:PASS@SERVER/DB?driver=ODBC+Driver+17+for+SQL+Server"
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,        # detecta conexiones muertas
    fast_executemany=True,     # mejora inserts masivos en SQL Server
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()