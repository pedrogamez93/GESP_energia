from __future__ import annotations

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TipoUso(Base):
    __tablename__ = "TipoUsos"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<TipoUso Id={self.Id} Nombre={self.Nombre!r}>"
