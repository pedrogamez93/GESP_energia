from __future__ import annotations

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Region(Base):
    __tablename__ = "Regiones"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(Integer, primary_key=True)
    Nombre: Mapped[str] = mapped_column(String(256))
    Numero: Mapped[int | None] = mapped_column(Integer)     # <- agregado
    Posicion: Mapped[int | None] = mapped_column(Integer)   # <- agregado

    comunas: Mapped[list["Comuna"]] = relationship("Comuna", back_populates="region")


class Comuna(Base):
    __tablename__ = "Comunas"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ProvinciaId: Mapped[int] = mapped_column(Integer, nullable=False)
    RegionId: Mapped[int] = mapped_column(Integer, ForeignKey("dbo.Regiones.Id"), nullable=False)
    Nombre: Mapped[str] = mapped_column(String(256))

    region: Mapped["Region"] = relationship("Region", back_populates="comunas")
