# app/db/models/entorno.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Entorno(Base):
    __tablename__ = "Entornos"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=0)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)
    Nombre:     Mapped[str | None] = mapped_column(Text)
