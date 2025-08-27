# app/db/models/edificio.py
from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.db.base import Base

class Edificio(Base):
    __tablename__ = "Edificios"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=1)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    Direccion: Mapped[str | None] = mapped_column(Text)
    Numero:    Mapped[str | None] = mapped_column(Text)
    Calle:     Mapped[str | None] = mapped_column(Text)

    Latitud:  Mapped[float | None] = mapped_column(Float)
    Longitud: Mapped[float | None] = mapped_column(Float)
    Altitud:  Mapped[float | None] = mapped_column(Float)

    TipoEdificioId:    Mapped[int | None] = mapped_column(BigInteger)
    ComunaId:          Mapped[int | None] = mapped_column(BigInteger)
    OldId:             Mapped[int | None] = mapped_column(Integer)
    TipoAgrupamientoId:Mapped[int | None] = mapped_column(BigInteger)
    EntornoId:         Mapped[int | None] = mapped_column(BigInteger)
    InerciaTermicaId:  Mapped[int | None] = mapped_column(BigInteger)
    FrontisId:         Mapped[int | None] = mapped_column(BigInteger)

    DpP1: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    DpP2: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    DpP3: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    DpP4: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
