# app/db/models/tipo_edificio.py
from __future__ import annotations

from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TipoEdificio(Base):
    __tablename__ = "TipoEdificios"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)
    OldId: Mapped[int | None] = mapped_column(BigInteger)
