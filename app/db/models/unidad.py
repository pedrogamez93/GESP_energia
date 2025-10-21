# app/db/models/unidad.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import (
    BigInteger, Integer, Text, Boolean, DateTime,
    ForeignKey, String, PrimaryKeyConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Unidad(Base):
    __tablename__ = "Unidades"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    Version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    Active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy: Mapped[str | None] = mapped_column(Text)

    # Negocio
    ServicioId: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dbo.Servicios.Id"))
    ChkNombre: Mapped[int | None] = mapped_column(Integer)  # (existe en la BD)
    OldId: Mapped[int | None] = mapped_column(BigInteger)
    Nombre: Mapped[str] = mapped_column(String(512), nullable=False)
    Funcionarios: Mapped[int | None] = mapped_column(Integer)
    IndicadorEE: Mapped[bool] = mapped_column(Boolean, default=False)
    AccesoFactura: Mapped[int | None] = mapped_column(Integer)
    InstitucionResponsableId: Mapped[int | None] = mapped_column(Integer)
    ServicioResponsableId: Mapped[int | None] = mapped_column(Integer)
    OrganizacionResponsable: Mapped[str | None] = mapped_column(Text)
    ReportaPMG: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relaciones puente
    unidad_inmuebles: Mapped[list["UnidadInmueble"]] = relationship(
        "UnidadInmueble", back_populates="unidad", cascade="all, delete-orphan"
    )
    unidad_pisos: Mapped[list["UnidadPiso"]] = relationship(
        "UnidadPiso", back_populates="unidad", cascade="all, delete-orphan"
    )
    unidad_areas: Mapped[list["UnidadArea"]] = relationship(
        "UnidadArea", back_populates="unidad", cascade="all, delete-orphan"
    )


class UnidadInmueble(Base):
    __tablename__ = "UnidadesInmuebles"
    __table_args__ = (
        PrimaryKeyConstraint("UnidadId", "InmuebleId", name="PK_UnidadesInmuebles"),
        {"schema": "dbo"},
    )

    UnidadId: Mapped[int] = mapped_column(BigInteger, ForeignKey("dbo.Unidades.Id", ondelete="CASCADE"), nullable=False)
    InmuebleId: Mapped[int] = mapped_column(BigInteger, nullable=False)

    unidad: Mapped["Unidad"] = relationship("Unidad", back_populates="unidad_inmuebles")


class UnidadPiso(Base):
    __tablename__ = "UnidadesPisos"
    __table_args__ = (
        PrimaryKeyConstraint("UnidadId", "PisoId", name="PK_UnidadesPisos"),
        {"schema": "dbo"},
    )

    UnidadId: Mapped[int] = mapped_column(BigInteger, ForeignKey("dbo.Unidades.Id", ondelete="CASCADE"), nullable=False)
    PisoId: Mapped[int] = mapped_column(BigInteger, nullable=False)

    unidad: Mapped["Unidad"] = relationship("Unidad", back_populates="unidad_pisos")


class UnidadArea(Base):
    __tablename__ = "UnidadesAreas"
    __table_args__ = (
        PrimaryKeyConstraint("UnidadId", "AreaId", name="PK_UnidadesAreas"),
        {"schema": "dbo"},
    )

    UnidadId: Mapped[int] = mapped_column(BigInteger, ForeignKey("dbo.Unidades.Id", ondelete="CASCADE"), nullable=False)
    AreaId: Mapped[int] = mapped_column(BigInteger, nullable=False)

    unidad: Mapped["Unidad"] = relationship("Unidad", back_populates="unidad_areas")
