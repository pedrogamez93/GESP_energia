# app/db/models/inercia_termica.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class InerciaTermica(Base):
    __tablename__ = "InerciaTermicas"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=1)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    CreatedBy: Mapped[str | None] = mapped_column(Text)
    ModifiedBy:Mapped[str | None] = mapped_column(Text)

    Nombre: Mapped[str | None] = mapped_column(Text)
    OldId:  Mapped[int | None] = mapped_column(BigInteger)
