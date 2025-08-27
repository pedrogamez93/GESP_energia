# app/db/models/tipo_agrupamiento.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TipoAgrupamiento(Base):
    __tablename__ = "TipoAgrupamientos"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)
    Active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    CreatedBy: Mapped[str | None] = mapped_column(Text)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
