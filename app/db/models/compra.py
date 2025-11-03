# app/db/models/compra.py
from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Text,
    Index,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Compra(Base):
    __tablename__ = "Compras"
    __table_args__ = (
        Index("IX_Compras_FechaCompra_Id", "FechaCompra", "Id"),
        Index("IX_Compras_DivisionId", "DivisionId"),
        Index("IX_Compras_EnergeticoId", "EnergeticoId"),
        Index("IX_Compras_NumeroClienteId", "NumeroClienteId"),
        Index("IX_Compras_Active", "Active"),
        {"schema": "dbo"},
    )

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=text("GETDATE()")
    )
    UpdatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=text("GETDATE()")
    )
    Version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    Active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(Text, nullable=True)
    CreatedBy: Mapped[str | None] = mapped_column(Text, nullable=True)

    Consumo: Mapped[float] = mapped_column(Float, nullable=False)
    InicioLectura: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    FinLectura: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    NumeroClienteId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    DivisionId: Mapped[int] = mapped_column(BigInteger, nullable=False)
    EnergeticoId: Mapped[int] = mapped_column(BigInteger, nullable=False)

    FechaCompra: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Costo: Mapped[float] = mapped_column(Float, nullable=False)

    Observacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    FacturaId: Mapped[int] = mapped_column(BigInteger, nullable=False)
    UnidadMedidaId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    EstadoValidacionId: Mapped[str | None] = mapped_column(Text, nullable=True)
    RevisadoPor: Mapped[str | None] = mapped_column(Text, nullable=True)
    ReviewedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    CreatedByDivisionId: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ObservacionRevision: Mapped[str | None] = mapped_column(Text, nullable=True)

    SinMedidor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ─────────────────────────────────────────────────────────────
    # Relación SOLO LECTURA con CompraMedidor (join por columna)
    # ─────────────────────────────────────────────────────────────
    Items: Mapped[List["CompraMedidor"]] = relationship(
        "CompraMedidor",
        primaryjoin="Compra.Id == CompraMedidor.CompraId",
        viewonly=True,           # no intentará insertar/actualizar via relación
        lazy="selectin",         # eficiente para múltiples compras
        order_by="CompraMedidor.Id",
    )

    def __repr__(self) -> str:
        return (
            f"<Compra Id={self.Id} DivisionId={self.DivisionId} "
            f"EnergeticoId={self.EnergeticoId} FechaCompra={self.FechaCompra!s}>"
        )
