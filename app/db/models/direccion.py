from __future__ import annotations
from sqlalchemy import BigInteger, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Direccion(Base):
    __tablename__ = "Direcciones"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Calle: Mapped[str | None] = mapped_column(Text)
    Numero: Mapped[str | None] = mapped_column(Text)
    DireccionCompleta: Mapped[str | None] = mapped_column(Text)
    RegionId: Mapped[int | None] = mapped_column(BigInteger)
    ProvinciaId: Mapped[int | None] = mapped_column(BigInteger)
    ComunaId: Mapped[int | None] = mapped_column(BigInteger)
