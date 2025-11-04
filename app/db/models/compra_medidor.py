from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Text,
    Index,
    ForeignKey,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .compra import Compra
    from .medidor import Medidor


class CompraMedidor(Base):
    __tablename__ = "CompraMedidor"
    __table_args__ = (
        Index("IX_CompraMedidor_CompraId", "CompraId"),
        Index("IX_CompraMedidor_MedidorId", "MedidorId"),
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

    ModifiedBy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    CreatedBy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Datos
    CompraId: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dbo.Compras.Id", ondelete="NO ACTION"),
        nullable=False,
    )
    MedidorId: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("dbo.Medidores.Id", ondelete="NO ACTION"),
        nullable=True,  # puede venir null si es 'SinMedidor'
    )

    Consumo: Mapped[float] = mapped_column(Float, nullable=False)

    ParametroMedicionId: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    UnidadMedidaId: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # ─────────────────────────────────────────────────────────────
    # Relaciones SOLO LECTURA (eval diferida con lambda)
    # ─────────────────────────────────────────────────────────────
    compra: Mapped["Compra"] = relationship(
        "Compra",
        primaryjoin=lambda: CompraMedidor.CompraId == Compra.Id,
        foreign_keys=lambda: [CompraMedidor.CompraId],
        viewonly=True,
        lazy="joined",
    )

    medidor: Mapped[Optional["Medidor"]] = relationship(
        "Medidor",
        primaryjoin=lambda: CompraMedidor.MedidorId == Medidor.Id,
        foreign_keys=lambda: [CompraMedidor.MedidorId],
        viewonly=True,
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<CompraMedidor Id={self.Id} CompraId={self.CompraId} "
            f"MedidorId={self.MedidorId} Consumo={self.Consumo}>"
        )
