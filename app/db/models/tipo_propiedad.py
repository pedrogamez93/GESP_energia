from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TipoPropiedad(Base):
    __tablename__ = "TipoPropiedades"
    __table_args__ = {"schema": "dbo"}

    # En SQL Server tu PK es INT -> usa Integer (no BigInteger)
    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    Nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)
    Orden:  Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Backref opcional hacia Division (no string, importaremos Division en el otro modelo)
    divisiones = relationship(
        "Division",
        back_populates="tipo_propiedad",
        lazy="noload",
        cascade="save-update, merge",
    )
