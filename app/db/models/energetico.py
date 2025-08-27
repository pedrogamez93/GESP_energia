# app/db/models/energetico.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    BigInteger, Integer, Text, Boolean, DateTime, Float, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Energetico(Base):
    __tablename__ = "Energeticos"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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

    # ───────── Relaciones ─────────
    unidades_medidas: Mapped[list["app.db.models.energetico.EnergeticoUnidadMedida"]] = relationship(
        "app.db.models.energetico.EnergeticoUnidadMedida",
        back_populates="energetico",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # 👉 apuntamos al modelo que está en energetico_division.py
    divisiones: Mapped[list["app.db.models.energetico_division.EnergeticoDivision"]] = relationship(
        "app.db.models.energetico_division.EnergeticoDivision",
        back_populates="energetico",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class EnergeticoUnidadMedida(Base):
    __tablename__ = "EnergeticoUnidadesMedidas"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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

    energetico: Mapped["app.db.models.energetico.Energetico"] = relationship(
        "app.db.models.energetico.Energetico",
        back_populates="unidades_medidas",
        passive_deletes=True,
    )

    # Si no hay ambigüedad, esto puede quedar corto:
    # unidad_medida: Mapped["UnidadMedida"] = relationship("UnidadMedida")
    # O calificado si prefieres:
    # unidad_medida: Mapped["app.db.models.unidad_medida.UnidadMedida"] = relationship(
    #     "app.db.models.unidad_medida.UnidadMedida"
    # )
