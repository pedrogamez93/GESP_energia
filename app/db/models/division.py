from __future__ import annotations
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, Integer, Text, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.tipo_propiedad import TipoPropiedad   # IMPORTA la clase

class Division(Base):
    __tablename__ = "Divisiones"
    __table_args__ = {"schema": "dbo"}

    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Metadatos / estado
    CreatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)

    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    # Datos base obligatorios
    Funcionarios:     Mapped[int]        = mapped_column(Integer, nullable=False)
    Nombre:           Mapped[str | None] = mapped_column(Text)
    ReportaPMG:       Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    AnyoConstruccion: Mapped[int]        = mapped_column(Integer, nullable=False)

    # Geo
    Latitud:  Mapped[float | None] = mapped_column(Float)
    Longitud: Mapped[float | None] = mapped_column(Float)

    # FKs principales (revisa tipos reales de Edificios/Servicios; si sus PKs son INT, cámbialos a Integer)
    EdificioId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Edificios.Id", ondelete="CASCADE"), nullable=False
    )
    ServicioId: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dbo.Servicios.Id", ondelete="CASCADE"), nullable=False
    )
    # >>> tu tabla TipoPropiedades.Id es INT -> usa Integer aquí para que no haya desajuste
    TipoPropiedadId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dbo.TipoPropiedades.Id", name="FK_Divisiones_TipoPropiedades"),
        nullable=False,
    )

    # Relación ORM (usa la clase, no string)
    tipo_propiedad: Mapped[TipoPropiedad] = relationship(
        TipoPropiedad,
        back_populates="divisiones",
        lazy="joined",
        foreign_keys="Division.TipoPropiedadId",
    )

    # --- resto de columnas (igual que tenías) ---
    TipoUnidadId:       Mapped[int | None] = mapped_column(BigInteger)
    Superficie:         Mapped[float | None] = mapped_column(Float)
    Pisos:              Mapped[str | None] = mapped_column(Text)
    TipoUsoId:          Mapped[int | None] = mapped_column(BigInteger)
    NroRol:             Mapped[str | None] = mapped_column(Text)
    Direccion:          Mapped[str | None] = mapped_column(Text)

    ComparteMedidorElectricidad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ComparteMedidorGasCanieria:  Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    PisosIguales:                Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    NivelPaso3:                  Mapped[int]  = mapped_column(Integer, nullable=False, default=0)

    Calle:     Mapped[str | None] = mapped_column(Text)
    ComunaId:  Mapped[int | None] = mapped_column(BigInteger)
    Numero:    Mapped[str | None] = mapped_column(Text)

    GeVersion:                 Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    ParentId:                  Mapped[int | None] = mapped_column(BigInteger)
    ProvinciaId:               Mapped[int | None] = mapped_column(BigInteger)
    RegionId:                  Mapped[int | None] = mapped_column(BigInteger)
    TipoAdministracionId:      Mapped[int | None] = mapped_column(BigInteger)
    TipoInmueble:              Mapped[int | None] = mapped_column(BigInteger)
    AdministracionServicioId:  Mapped[int | None] = mapped_column(BigInteger)

    DpSt1: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    DpSt2: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    DpSt3: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    DpSt4: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    DireccionInmuebleId: Mapped[int | None] = mapped_column(BigInteger)
    AccesoFactura:       Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    OrganizacionResponsable: Mapped[str | None] = mapped_column(Text)
    ServicioResponsableId:   Mapped[int | None] = mapped_column(Integer)
    InstitucionResponsableId:Mapped[int | None] = mapped_column(Integer)
    IndicadorEE:             Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    JustificaRol:            Mapped[str | None] = mapped_column(Text)
    SinRol:                  Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)

    Compromiso2022:           Mapped[bool | None] = mapped_column(Boolean)
    Justificacion:            Mapped[str | None]  = mapped_column(Text)
    ObservacionCompromiso2022:Mapped[str | None]  = mapped_column(Text)
    EstadoCompromiso2022:     Mapped[int | None]  = mapped_column(Integer)
    AnioInicioGestionEnergetica: Mapped[int | None] = mapped_column(Integer)
    AnioInicioRestoItems:        Mapped[int | None] = mapped_column(Integer)

    DisponeVehiculo: Mapped[bool | None] = mapped_column(Boolean)
    VehiculosIds:    Mapped[str | None]  = mapped_column(Text)

    AireAcondicionadoElectricidad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    CalefaccionGas:                Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    DisponeCalefaccion:            Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    NroOtrosColaboradores: Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    ObservacionPapel:      Mapped[str | None] = mapped_column(Text)
    ObservaPapel:          Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    ObservacionResiduos:   Mapped[str | None] = mapped_column(Text)
    ObservaResiduos:       Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    ObservacionAgua:       Mapped[str | None] = mapped_column(Text)
    ObservaAgua:           Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    JustificaResiduos:     Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    JustificacionResiduos: Mapped[str | None] = mapped_column(Text)

    ReportaEV:                Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    TieneMedidorElectricidad: Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    TieneMedidorGas:          Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    AccesoFacturaAgua:        Mapped[int | None] = mapped_column(Integer)
    InstitucionResponsableAguaId: Mapped[int | None] = mapped_column(Integer)
    OrganizacionResponsableAgua:  Mapped[str | None] = mapped_column(Text)
    ServicioResponsableAguaId:    Mapped[int | None] = mapped_column(Integer)
    ComparteMedidorAgua:          Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)

    NoDeclaraImpresora:  Mapped[bool | None] = mapped_column(Boolean)
    NoDeclaraArtefactos: Mapped[bool | None] = mapped_column(Boolean)
    NoDeclaraContenedores: Mapped[bool | None] = mapped_column(Boolean)
    GestionBienes:         Mapped[bool | None] = mapped_column(Boolean)

    UsaBidon:                        Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    JustificaResiduosNoReciclados:   Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    JustificacionResiduosNoReciclados: Mapped[str | None] = mapped_column(Text)

    ColectorId:                Mapped[int | None] = mapped_column(BigInteger)
    EnergeticoAcsId:           Mapped[int | None] = mapped_column(BigInteger)
    EnergeticoCalefaccionId:   Mapped[int | None] = mapped_column(BigInteger)
    EnergeticoRefrigeracionId: Mapped[int | None] = mapped_column(BigInteger)
    EquipoAcsId:               Mapped[int | None] = mapped_column(BigInteger)
    EquipoCalefaccionId:       Mapped[int | None] = mapped_column(BigInteger)
    EquipoRefrigeracionId:     Mapped[int | None] = mapped_column(BigInteger)

    FotoTecho:   Mapped[bool]         = mapped_column(Boolean, nullable=False, default=False)
    ImpSisFv:    Mapped[bool]         = mapped_column(Boolean, nullable=False, default=False)
    InstTerSisFv:Mapped[bool]         = mapped_column(Boolean, nullable=False, default=False)
    PotIns:      Mapped[float | None] = mapped_column(Float)
    SistemaSolarTermico: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    SupColectores:   Mapped[float | None] = mapped_column(Float)
    SupFotoTecho:    Mapped[float | None] = mapped_column(Float)
    SupImptSisFv:    Mapped[float | None] = mapped_column(Float)
    SupInstTerSisFv: Mapped[float | None] = mapped_column(Float)

    TempSeteoCalefaccionId: Mapped[int | None] = mapped_column(BigInteger)
    TempSeteoRefrigeracionId: Mapped[int | None] = mapped_column(BigInteger)
    TipoLuminariaId:        Mapped[int | None] = mapped_column(BigInteger)
    MantColectores:         Mapped[int | None] = mapped_column(Integer)
    MantSfv:                Mapped[int | None] = mapped_column(Integer)

    CargaPosteriorT: Mapped[bool]         = mapped_column(Boolean, nullable=False, default=False)
    IndicadorEnegia: Mapped[float | None] = mapped_column(Float)
    ObsInexistenciaEyV: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<Division Id={self.Id} Nombre={self.Nombre!r} Active={self.Active}>"
