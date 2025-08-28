from __future__ import annotations
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Piso(Base):
    __tablename__ = "Pisos"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # metadatos
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=1)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    # dominio (según Entities/Piso.cs)
    Superficie:  Mapped[float] = mapped_column(Float, nullable=False, default=0)
    Altura:      Mapped[float] = mapped_column(Float, nullable=False, default=0)
    NumeroPisoId:Mapped[int]   = mapped_column(BigInteger, nullable=False)
    TipoUsoId:   Mapped[int | None] = mapped_column(BigInteger)
    EdificioId:  Mapped[int | None] = mapped_column(BigInteger)
    DivisionId:  Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dbo.Divisiones.Id"))
