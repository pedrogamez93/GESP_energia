from __future__ import annotations

from sqlalchemy import BigInteger, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CompraMedidor(Base):
    __tablename__ = "CompraMedidor"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    Consumo: Mapped[float] = mapped_column(Float, nullable=False)

    MedidorId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Medidores.Id", ondelete=None), nullable=False
    )
    CompraId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Compras.Id", ondelete="CASCADE"), nullable=False
    )
    ParametroMedicionId: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("dbo.ParametrosMedicion.Id", ondelete=None), nullable=True
    )
    UnidadMedidaId: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("dbo.UnidadesMedida.Id", ondelete=None), nullable=True
    )
