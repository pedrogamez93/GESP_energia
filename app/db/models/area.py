from __future__ import annotations
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Area(Base):
    __tablename__ = "Areas"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # metadatos
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=1)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    # dominio
    Nombre:     Mapped[str | None] = mapped_column(Text)
    Superficie: Mapped[float]      = mapped_column(Numeric(18, 2), nullable=False, default=0)
    TipoUsoId:  Mapped[int]        = mapped_column(BigInteger, nullable=False)
    PisoId:     Mapped[int]        = mapped_column(BigInteger, ForeignKey("dbo.Pisos.Id"), nullable=False)
