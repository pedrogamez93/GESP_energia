# app/db/models/tipo_colector.py
from __future__ import annotations

from sqlalchemy import BigInteger, Text, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TipoColector(Base):
    __tablename__ = "TiposColectores"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)
    # En BD hay valores como 'c', 'sf'; dejamos margen.
    Tipo: Mapped[str | None] = mapped_column(String(10))
