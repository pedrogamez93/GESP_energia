# app/db/models/tipo_propiedad.py
from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TipoPropiedad(Base):
    __tablename__ = "TipoPropiedades"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)
    Active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Backref a divisiones (no carga por defecto para no sobre-joinnear)
    divisiones: Mapped[list["Division"]] = relationship(
        "Division",
        back_populates="tipo_propiedad",
        lazy="noload",
    )
