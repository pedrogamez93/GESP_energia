from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Medidor(Base):
    __tablename__ = "Medidores"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=0)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    Numero:            Mapped[str | None] = mapped_column(Text)
    NumeroClienteId:   Mapped[int]        = mapped_column(BigInteger, nullable=False)
    Fases:             Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    Smart:             Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    Compartido:        Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    DivisionId:        Mapped[int | None] = mapped_column(BigInteger)
    Factura:           Mapped[bool | None] = mapped_column(Boolean)
    Chilemedido:       Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    DeviceId:          Mapped[int | None] = mapped_column(Integer)
    MedidorConsumo:    Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
