from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

# ==============================
# dbo.MedidoresInteligentes
# ==============================
class MedidorInteligente(Base):
    __tablename__ = "MedidoresInteligentes"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # control
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=0)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    # datos
    ChileMedidoId: Mapped[int] = mapped_column(BigInteger, nullable=False)


# ======================================
# pivotes: Divisiones / Edificios / Servicios
# ======================================
class MedidorInteligenteDivision(Base):
    __tablename__ = "MedidorInteligenteDivisiones"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=0)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    MedidorInteligenteId: Mapped[int] = mapped_column(BigInteger, nullable=False)
    DivisionId:            Mapped[int] = mapped_column(BigInteger, nullable=False)


class MedidorInteligenteEdificio(Base):
    __tablename__ = "MedidorInteligenteEdificios"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=0)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    MedidorInteligenteId: Mapped[int] = mapped_column(BigInteger, nullable=False)
    EdificioId:            Mapped[int] = mapped_column(BigInteger, nullable=False)


class MedidorInteligenteServicio(Base):
    __tablename__ = "MedidorInteligenteServicios"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=0)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    MedidorInteligenteId: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ServicioId:            Mapped[int] = mapped_column(BigInteger, nullable=False)
