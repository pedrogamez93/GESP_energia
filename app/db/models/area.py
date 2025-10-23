# app/db/models/area.py
from __future__ import annotations
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Numeric, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Area(Base):
    __tablename__ = "Areas"
    __table_args__ = {"schema": "dbo"}

    # PK
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Metadatos (no ponemos defaults de server; se setean en service)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=1)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    # Dominio (columnas reales)
    Nombre:     Mapped[str | None] = mapped_column(Text, nullable=True)
    Superficie: Mapped[float]      = mapped_column(Numeric(18, 2), nullable=False, default=0)
    TipoUsoId:  Mapped[int]        = mapped_column(BigInteger, nullable=False)
    PisoId:     Mapped[int]        = mapped_column(BigInteger, ForeignKey("dbo.Pisos.Id"), nullable=False)

    # Existe en BD (según tu tabla), pero NO lo estabas usando en schema:
    # si no lo vas a usar, puedes dejarlo nullable y sin tocar schemas
    NroRol:     Mapped[int | None] = mapped_column(BigInteger, nullable=True)
