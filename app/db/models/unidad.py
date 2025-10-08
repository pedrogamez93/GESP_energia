# app/db/models/unidad.py
from __future__ import annotations
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Unidad(Base):
    __tablename__ = "Unidades"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # (no necesitas más campos para resolver el FK)
