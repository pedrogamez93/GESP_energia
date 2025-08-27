# app/db/models/energetico_division.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EnergeticoDivision(Base):
    __tablename__ = "EnergeticoDivision"
    __table_args__ = {"schema": "dbo"}  # no uses extend_existing aquí

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=0)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(Text, nullable=True)
    CreatedBy:  Mapped[str | None] = mapped_column(Text, nullable=True)

    DivisionId:      Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 🔑 ForeignKey explícita para que SQLAlchemy pueda inferir el join
    EnergeticoId:    Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Energeticos.Id", ondelete="CASCADE"), nullable=False
    )
    NumeroClienteId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # ───────── Relaciones ─────────
    energetico: Mapped["app.db.models.energetico.Energetico"] = relationship(
        "app.db.models.energetico.Energetico",
        back_populates="divisiones",
        passive_deletes=True,
    )
