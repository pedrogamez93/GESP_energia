from __future__ import annotations

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TipoPropiedad(Base):
    __tablename__ = "TipoPropiedades"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)
    Orden: Mapped[int | None] = mapped_column(Integer)

    # 👇 ESTA ES LA RELACIÓN QUE TE FALTABA (para calzar con Division.back_populates="divisiones")
    divisiones: Mapped[list["Division"]] = relationship(
        "Division",
        back_populates="tipo_propiedad",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<TipoPropiedad Id={self.Id} Nombre={self.Nombre!r}>"
