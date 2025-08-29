from __future__ import annotations

from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class ParametroMedicion(Base):
    __tablename__ = "ParametrosMedicion"
    __table_args__ = {"schema": "dbo"}

    # Mínimo viable para cumplir con FKs de CompraMedidor
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)
