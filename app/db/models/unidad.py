# app/db/models/unidad.py
from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# =======================
#   Tabla principal
# =======================
class Unidad(Base):
    __tablename__ = "Unidades"
    __table_args__ = ({"schema": "dbo"},)

    # --- PK ---
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # --- Metadatos / auditoría ---
    CreatedAt: Mapped["DateTime | None"] = mapped_column(DateTime, nullable=True)
    UpdatedAt: Mapped["DateTime | None"] = mapped_column(DateTime, nullable=True)
    Version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ModifiedBy: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    CreatedBy: Mapped[str | None] = mapped_column(String(length=255), nullable=True)

    # --- Datos de la unidad ---
    Nombre: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    ServicioId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ChkNombre: Mapped[int | None] = mapped_column(Integer, nullable=True)
    OldId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    AccesoFactura: Mapped[int | None] = mapped_column(Integer, nullable=True)

    InstitucionResponsableId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ServicioResponsableId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    OrganizacionResponsable: Mapped[str | None] = mapped_column(String(length=255), nullable=True)

    ReportaPMG: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    IndicadorEE: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    Funcionarios: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relaciones ORM (no crean tablas; solo mapeo lógico)
    unidad_inmuebles: Mapped[list["UnidadInmueble"]] = relationship(
        "UnidadInmueble", back_populates="unidad", cascade="all, delete-orphan"
    )

    # Nota:
    # Las relaciones con Pisos y Áreas ya no necesitan clases pivote aquí.
    # Se gestionan mediante los Table(...) en:
    #   - app/db/models/unidades_pisos.py
    #   - app/db/models/unidades_areas.py


# =======================
#   Pivote: Unidades <-> Divisiones (Inmuebles)
# =======================
class UnidadInmueble(Base):
    __tablename__ = "UnidadesInmuebles"
    __table_args__ = ({"schema": "dbo"},)

    UnidadId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    InmuebleId: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    unidad: Mapped["Unidad"] = relationship("Unidad", back_populates="unidad_inmuebles")
