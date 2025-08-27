from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Equipo(Base):
    __tablename__ = "Equipos"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Timestamps / control
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=0)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    # FKs / referencias (ids “crudos” para calzar con el SQL actual)
    TipoTecnologiaId: Mapped[int] = mapped_column(BigInteger, nullable=False)
    SistemaId:        Mapped[int] = mapped_column(BigInteger, nullable=False)
    ModoOperacionId:  Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Energéticos
    EnergeticoIn:   Mapped[int] = mapped_column(BigInteger, nullable=False)
    EnergeticoOut:  Mapped[int] = mapped_column(BigInteger, nullable=False)
    EnergeticInId:  Mapped[int | None] = mapped_column(BigInteger)
    EnergeticOutId: Mapped[int | None] = mapped_column(BigInteger)

    DivisionId: Mapped[int | None] = mapped_column(BigInteger)

    # Atributos técnicos / costos
    AnyoCompra:      Mapped[int]   = mapped_column(Integer, nullable=False)
    HorasUso:        Mapped[float] = mapped_column(Float,   nullable=False)
    Marca:           Mapped[str | None] = mapped_column(Text)
    Modelo:          Mapped[str | None] = mapped_column(Text)
    Potencia:        Mapped[float] = mapped_column(Float,   nullable=False)
    Cantidad:        Mapped[int]   = mapped_column(Integer, nullable=False)
    Inversion:       Mapped[int]   = mapped_column(Integer, nullable=False)
    CostoMantencion: Mapped[int]   = mapped_column(Integer, nullable=False)
