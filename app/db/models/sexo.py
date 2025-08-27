# app/db/models/sexo.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Sexo(Base):
    __tablename__ = "Sexo"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Campos mínimos; ajusta si tu tabla real tiene más columnas
    Nombre:    Mapped[str | None] = mapped_column(Text)
    Active:    Mapped[bool]       = mapped_column(Boolean, nullable=False, default=True)
    CreatedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    UpdatedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
