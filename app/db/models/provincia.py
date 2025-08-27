# app/db/models/provincia.py
from __future__ import annotations
from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Provincia(Base):
    __tablename__ = "Provincias"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    RegionId: Mapped[int] = mapped_column(BigInteger)
    Nombre: Mapped[str | None] = mapped_column(Text)
