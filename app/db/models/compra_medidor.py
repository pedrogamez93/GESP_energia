# app/db/models/compra_medidor.py
from __future__ import annotations
from typing import Optional

from sqlalchemy import BigInteger, Float, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CompraMedidor(Base):
    __tablename__ = "CompraMedidor"
    __table_args__ = (
        Index("IX_CompraMedidor_CompraId", "CompraId"),
        Index("IX_CompraMedidor_MedidorId", "MedidorId"),
        {"schema": "dbo"},
    )

    # Columnas REALES en dbo.CompraMedidor (según tus capturas)
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CompraId:  Mapped[int]           = mapped_column(BigInteger, ForeignKey("dbo.Compras.Id"), nullable=False)
    MedidorId: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("dbo.Medidores.Id"), nullable=True)

    Consumo:             Mapped[float]        = mapped_column(Float, nullable=False)
    ParametroMedicionId: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    UnidadMedidaId:      Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Relación a Medidor (se mantiene igual)
    medidor: Mapped[Optional["Medidor"]] = relationship(
        "Medidor",
        primaryjoin="CompraMedidor.MedidorId == Medidor.Id",
        viewonly=True,
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<CompraMedidor Id={self.Id} CompraId={self.CompraId} MedidorId={self.MedidorId} Consumo={self.Consumo}>"
