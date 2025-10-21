from __future__ import annotations
from datetime import datetime

from sqlalchemy import (
    BigInteger, Integer, Text, Boolean, DateTime, String,
    ForeignKey, PrimaryKeyConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Unidad(Base):
    __tablename__ = "Unidades"
    __table_args__ = {"schema": "dbo"}
    # … columnas …

    # ← usar la clase externa, NO declarar otra
    unidad_inmuebles: Mapped[list["app.db.models.unidad_inmueble.UnidadInmueble"]] = relationship(
        "app.db.models.unidad_inmueble.UnidadInmueble",
        back_populates="unidad",
        cascade="all, delete-orphan",
    )

    unidad_pisos: Mapped[list["UnidadPiso"]] = relationship(
        "UnidadPiso", back_populates="unidad", cascade="all, delete-orphan"
    )
    unidad_areas: Mapped[list["UnidadArea"]] = relationship(
        "UnidadArea", back_populates="unidad", cascade="all, delete-orphan"
    )

# ⚠️ ELIMINAR COMPLETAMENTE la clase UnidadInmueble que estaba aquí
# class UnidadInmueble(Base):
#     __tablename__ = "UnidadesInmuebles"
#     __table_args__ = (PrimaryKeyConstraint("UnidadId","InmuebleId", name="PK_UnidadesInmuebles"), {"schema":"dbo"})
#     … <todo el bloque> …

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
