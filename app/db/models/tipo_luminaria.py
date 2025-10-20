from __future__ import annotations
from sqlalchemy import BigInteger, Text, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TipoLuminaria(Base):
    __tablename__ = "TiposLuminarias"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    Nombre: Mapped[str | None] = mapped_column(Text)

    # Campos técnicos/económicos (según DDL)
    Q_Educacion: Mapped[float] = mapped_column(Float, nullable=False)
    Q_Oficinas: Mapped[float] = mapped_column(Float, nullable=False)
    Q_Salud: Mapped[float] = mapped_column(Float, nullable=False)
    Q_Seguridad: Mapped[float] = mapped_column(Float, nullable=False)

    Area_Educacion: Mapped[float] = mapped_column(Float, nullable=False)
    Area_Oficinas: Mapped[float] = mapped_column(Float, nullable=False)
    Area_Salud: Mapped[float] = mapped_column(Float, nullable=False)
    Area_Seguridad: Mapped[float] = mapped_column(Float, nullable=False)

    Vida_Util: Mapped[int] = mapped_column(Integer, nullable=False)
    Costo_Lamp: Mapped[int] = mapped_column(Integer, nullable=False)
    Costo_Lum: Mapped[int] = mapped_column(Integer, nullable=False)
    Costo_Social_Lamp: Mapped[int] = mapped_column(Integer, nullable=False)
    Costo_Social_Lum: Mapped[int] = mapped_column(Integer, nullable=False)

    Ejec_HD_Maestro: Mapped[float] = mapped_column(Float, nullable=False)
    Ejec_HD_Ayte: Mapped[float] = mapped_column(Float, nullable=False)
    Ejec_HD_Jornal: Mapped[float] = mapped_column(Float, nullable=False)

    Rep_HD_Maestro: Mapped[float] = mapped_column(Float, nullable=False)
    Rep_HD_Ayte: Mapped[float] = mapped_column(Float, nullable=False)
    Rep_HD_Jornal: Mapped[float] = mapped_column(Float, nullable=False)
