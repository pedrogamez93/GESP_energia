# app/db/models/unidad.py
from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Numeric, SmallInteger
from app.db.base import Base


class Unidad(Base):
    __tablename__ = "Unidades"
    __table_args__ = ({"schema": "dbo"},)

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    CreatedAt: Mapped["DateTime | None"] = mapped_column(DateTime, nullable=True)
    UpdatedAt: Mapped["DateTime | None"] = mapped_column(DateTime, nullable=True)
    Version:   Mapped[int | None]        = mapped_column(Integer, nullable=True)
    Active:    Mapped[bool | None]       = mapped_column(Boolean, nullable=True)
    ModifiedBy: Mapped[str | None]       = mapped_column(String(length=255), nullable=True)
    CreatedBy:  Mapped[str | None]       = mapped_column(String(length=255), nullable=True)

    Nombre:   Mapped[str | None]  = mapped_column(String(length=255), nullable=True)
    ServicioId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # En BD esta columna es NOT NULL; aquí la dejamos nullable=True para no romper el mapeo,
    # pero el servicio se encargará de ponerle valor SIEMPRE (1 por defecto).
    ChkNombre:  Mapped[int | None] = mapped_column(Integer, nullable=True)

    OldId:      Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    AccesoFactura: Mapped[int | None] = mapped_column(Integer, nullable=True)

    InstitucionResponsableId: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ServicioResponsableId:    Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    OrganizacionResponsable:  Mapped[str | None] = mapped_column(String(length=255), nullable=True)

    ReportaPMG:  Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    IndicadorEE: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    Funcionarios: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # =========================
    # ✅ NUEVOS CAMPOS (dbo.Unidades)
    # =========================
    TipoUsoId: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # DECIMAL(10,2)
    SuperficieM2: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    TipoPropiedadId: Mapped[int | None] = mapped_column(Integer, nullable=True)

    NumeroRol: Mapped[str | None] = mapped_column(String(length=50), nullable=True)

    # En BD es NOT NULL con DEFAULT(0) (tú ya lo creaste así)
    NoPoseeRol: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

    AnioConstruccion: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    OtrosColaboradores: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # NOT NULL DEFAULT(0)
    AccesoFacturaAgua: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

    ConsumeElectricidad: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    ComparteMedidorElectricidad: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

    ConsumeGas: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    ComparteMedidorGas: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

    ConsumeAgua: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    ComparteMedidorAgua: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

    # Relación con la pivote (requiere FKs válidos en UnidadInmueble)
    unidad_inmuebles: Mapped[list["UnidadInmueble"]] = relationship(
        "UnidadInmueble",
        back_populates="unidad",
        cascade="all, delete-orphan",
        primaryjoin="Unidad.Id == UnidadInmueble.UnidadId",
        foreign_keys="UnidadInmueble.UnidadId",
    )


class UnidadInmueble(Base):
    __tablename__ = "UnidadesInmuebles"
    __table_args__ = ({"schema": "dbo"},)

    UnidadId:   Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dbo.Unidades.Id", ondelete="RESTRICT"),
        primary_key=True,
    )
    InmuebleId: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dbo.Divisiones.Id", ondelete="RESTRICT"),
        primary_key=True,
    )

    # Relación inversa
    unidad: Mapped["Unidad"] = relationship(
        "Unidad",
        back_populates="unidad_inmuebles",
        primaryjoin="UnidadInmueble.UnidadId == Unidad.Id",
        foreign_keys=[UnidadId],
    )
