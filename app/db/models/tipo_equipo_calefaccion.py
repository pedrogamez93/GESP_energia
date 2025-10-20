from __future__ import annotations
from sqlalchemy import BigInteger, Text, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TipoEquipoCalefaccion(Base):
    __tablename__ = "TiposEquiposCalefaccion"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)

    # Parámetros y costos (según DDL)
    Rendimiento: Mapped[float] = mapped_column(Float, nullable=False)
    A: Mapped[float] = mapped_column(Float, nullable=False)
    B: Mapped[float] = mapped_column(Float, nullable=False)
    C: Mapped[float] = mapped_column(Float, nullable=False)
    Temp: Mapped[float] = mapped_column(Float, nullable=False)
    Costo: Mapped[float] = mapped_column(Float, nullable=False)
    Costo_Social: Mapped[float] = mapped_column(Float, nullable=False)
    Costo_Mant: Mapped[float] = mapped_column(Float, nullable=False)
    Costo_Social_Mant: Mapped[float] = mapped_column(Float, nullable=False)
    Ejec_HD_Maestro: Mapped[float] = mapped_column(Float, nullable=False)
    Ejec_HD_Ayte: Mapped[float] = mapped_column(Float, nullable=False)
    Ejec_HD_Jornal: Mapped[float] = mapped_column(Float, nullable=False)
    Mant_HD_Maestro: Mapped[float] = mapped_column(Float, nullable=False)
    Mant_HD_Ayte: Mapped[float] = mapped_column(Float, nullable=False)
    Mant_HD_Jornal: Mapped[float] = mapped_column(Float, nullable=False)

    # banderas de uso
    AC: Mapped[bool] = mapped_column(Boolean, nullable=False)
    CA: Mapped[bool] = mapped_column(Boolean, nullable=False)
    FR: Mapped[bool] = mapped_column(Boolean, nullable=False)
