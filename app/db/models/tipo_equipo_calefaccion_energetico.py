# app/db/models/tipo_equipo_calefaccion_energetico.py
from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TipoEquipoCalefaccionEnergetico(Base):
    __tablename__ = "TipoEquipoCalefaccionEnergetico"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    TipoEquipoCalefaccionId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.TiposEquiposCalefaccion.Id", ondelete="CASCADE"), nullable=False
    )
    EnergeticoId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Energeticos.Id", ondelete="CASCADE"), nullable=False
    )
