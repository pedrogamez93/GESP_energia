# app/db/models/energetico.py
from datetime import datetime  # <-- agrega esto
from sqlalchemy import (
    BigInteger, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Energetico(Base):
    __tablename__ = "Energeticos"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)   # <-- datetime (sin comillas)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)   # <-- idem
    Version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy: Mapped[str | None] = mapped_column(Text)

    Nombre: Mapped[str | None] = mapped_column(Text)
    Multiple: Mapped[bool] = mapped_column(Boolean, nullable=False)
    Icono: Mapped[str | None] = mapped_column(Text)
    PermiteMedidor: Mapped[bool] = mapped_column(Boolean, nullable=False)
    Posicion: Mapped[int] = mapped_column(Integer, nullable=False)
    OldId: Mapped[int | None] = mapped_column(BigInteger)
    PermitePotenciaSuministrada: Mapped[bool] = mapped_column(Boolean, nullable=False)
    PermiteTipoTarifa: Mapped[bool] = mapped_column(Boolean, nullable=False)

    unidades_medidas: Mapped[list["EnergeticoUnidadMedida"]] = relationship(
        "EnergeticoUnidadMedida", back_populates="energetico", cascade="all, delete-orphan"
    )
    divisiones: Mapped[list["EnergeticoDivision"]] = relationship(
        "EnergeticoDivision", back_populates="energetico", cascade="all, delete-orphan"
    )


class EnergeticoUnidadMedida(Base):
    __tablename__ = "EnergeticoUnidadesMedidas"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)   # <-- datetime
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)   # <-- datetime
    Version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy: Mapped[str | None] = mapped_column(Text)

    Calor: Mapped[float] = mapped_column(Float, nullable=False)
    Densidad: Mapped[float] = mapped_column(Float, nullable=False)
    Factor: Mapped[float] = mapped_column(Float, nullable=False)

    EnergeticoId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Energeticos.Id"), nullable=False
    )
    UnidadMedidaId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.UnidadesMedida.Id", ondelete="CASCADE"), nullable=False
    )

    energetico: Mapped["Energetico"] = relationship("Energetico", back_populates="unidades_medidas")
    unidad_medida: Mapped["UnidadMedida"] = relationship("UnidadMedida")


class EnergeticoDivision(Base):
    __tablename__ = "EnergeticoDivision"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)   # <-- datetime
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)   # <-- datetime
    Version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    Active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy: Mapped[str | None] = mapped_column(Text)

    DivisionId: Mapped[int] = mapped_column(BigInteger, nullable=False)
    EnergeticoId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Energeticos.Id", ondelete="CASCADE"), nullable=False
    )
    NumeroClienteId: Mapped[int | None] = mapped_column(BigInteger)

    energetico: Mapped["Energetico"] = relationship("Energetico", back_populates="divisiones")
