# app/db/models/tipo_equipo_calefaccion.py
from __future__ import annotations

from sqlalchemy import BigInteger, Text, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class TipoEquipoCalefaccion(Base):
    __tablename__ = "TiposEquiposCalefaccion"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Parámetros y costos (NOT NULL en DB -> defaults en ORM)
    Rendimiento: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    A: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    B: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    C: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Temp: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Costo: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Costo_Social: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Costo_Mant: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Costo_Social_Mant: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Ejec_HD_Maestro: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Ejec_HD_Ayte: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Ejec_HD_Jornal: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Mant_HD_Maestro: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Mant_HD_Ayte: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Mant_HD_Jornal: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    # Banderas
    AC: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    CA: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    FR: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
