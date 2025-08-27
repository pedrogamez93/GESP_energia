from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class NumeroCliente(Base):
    __tablename__ = "NumeroClientes"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Timestamps / control
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=0)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    # Datos de negocio (según SQL)
    Numero:           Mapped[str | None] = mapped_column(Text)
    NombreCliente:    Mapped[str | None] = mapped_column(Text)
    EmpresaDistribuidoraId: Mapped[int | None] = mapped_column(BigInteger)
    TipoTarifaId:           Mapped[int | None] = mapped_column(BigInteger)
    DivisionId:             Mapped[int | None] = mapped_column(BigInteger)
    PotenciaSuministrada:   Mapped[float]      = mapped_column(Float, nullable=False, default=0.0)
