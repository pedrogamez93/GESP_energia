from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Compra(Base):
    __tablename__ = "Compras"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=0)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(Text, nullable=True)
    CreatedBy:  Mapped[str | None] = mapped_column(Text, nullable=True)

    # Datos de la compra/lectura
    Consumo:       Mapped[float]   = mapped_column(Float, nullable=False)
    InicioLectura: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    FinLectura:    Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    NumeroClienteId:     Mapped[int | None] = mapped_column(BigInteger)
    DivisionId:          Mapped[int]        = mapped_column(BigInteger, nullable=False)
    EnergeticoId:        Mapped[int]        = mapped_column(BigInteger, nullable=False)
    FechaCompra:         Mapped[datetime]   = mapped_column(DateTime(timezone=False), nullable=False)
    Costo:               Mapped[float]      = mapped_column(Float, nullable=False)
    Observacion:         Mapped[str | None] = mapped_column(Text)
    FacturaId:           Mapped[int]        = mapped_column(BigInteger, nullable=False)
    UnidadMedidaId:      Mapped[int | None] = mapped_column(BigInteger)

    EstadoValidacionId:  Mapped[str | None] = mapped_column(Text)
    RevisadoPor:         Mapped[str | None] = mapped_column(Text)
    ReviewedAt:          Mapped[datetime | None] = mapped_column(DateTime(timezone=False))

    CreatedByDivisionId: Mapped[int]  = mapped_column(BigInteger, nullable=False)
    ObservacionRevision: Mapped[str | None] = mapped_column(Text)

    SinMedidor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
