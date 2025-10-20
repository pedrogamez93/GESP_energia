from __future__ import annotations
from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TipoColector(Base):
    # ⚠️ En BD es PLURAL
    __tablename__ = "TiposColectores"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)
    # En el DDL existe esta columna (nullable)
    Tipo: Mapped[str | None] = mapped_column(Text)
