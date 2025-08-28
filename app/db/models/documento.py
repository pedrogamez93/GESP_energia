from __future__ import annotations
from datetime import datetime
from sqlalchemy import (
    BigInteger, Integer, Boolean, DateTime, Text, Float, String, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, declared_attr
from app.db.base import Base

# ---------- Base con herencia de tabla única (Discriminator) ----------

class Documento(Base):
    __tablename__ = "Documentos"
    __table_args__ = {"schema": "dbo"}

    # PK y metadatos/auditoría
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False, default=1)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    ModifiedBy: Mapped[str | None] = mapped_column(Text)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)

    # Campos comunes
    Fecha: Mapped[datetime | None] = mapped_column(DateTime)
    AdjuntoUrl:    Mapped[str | None] = mapped_column(Text)
    AdjuntoNombre: Mapped[str | None] = mapped_column(Text)

    # Respaldos / adicionales
    AdjuntoRespaldoUrl:    Mapped[str | None] = mapped_column(Text)
    AdjuntoRespaldoNombre: Mapped[str | None] = mapped_column(Text)
    AdjuntoRespaldoUrlParticipativo:    Mapped[str | None] = mapped_column(Text)
    AdjuntoRespaldoNombreParticipativo: Mapped[str | None] = mapped_column(Text)
    AdjuntoRespaldoUrlCompromiso:       Mapped[str | None] = mapped_column(Text)
    AdjuntoRespaldoNombreCompromiso:    Mapped[str | None] = mapped_column(Text)

    # Texto y metadatos
    Nresolucion:   Mapped[str | None] = mapped_column(Text)
    Observaciones: Mapped[str | None] = mapped_column(String(500))
    Discriminator: Mapped[str]        = mapped_column(Text)  # importante para herencia
    TipoDocumentoId: Mapped[int]      = mapped_column(Integer, nullable=False, default=0)  # constants

    # Relaciones
    ServicioId: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("dbo.Servicios.Id", ondelete="NO ACTION")
    )
    ActaComiteId: Mapped[int | None] = mapped_column(BigInteger)  # self-FK uso puntual .NET
    TipoAdjunto:  Mapped[str | None] = mapped_column(Text)
    Titulo:       Mapped[str | None] = mapped_column(Text)
    Materia:      Mapped[str | None] = mapped_column(Text)

    # Banderas y enteros varios (subset principal del DDL; añade según necesites)
    Cobertura: Mapped[int | None] = mapped_column(Integer)
    EstandaresSustentabilidad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ProcesoGestionSustentable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ProdBajoImpactoAmbiental:  Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    Reciclaje:   Mapped[bool]  = mapped_column(Boolean, nullable=False, default=False)
    Reduccion:   Mapped[bool]  = mapped_column(Boolean, nullable=False, default=False)
    Reutilizacion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    ComprasSustentables:  Mapped[bool | None] = mapped_column(Boolean)
    EficienciaEnergetica: Mapped[bool | None] = mapped_column(Boolean)
    GestionPapel:         Mapped[bool | None] = mapped_column(Boolean)
    Otras:                Mapped[str | None]  = mapped_column(Text)

    DifusionInterna:   Mapped[bool | None] = mapped_column(Boolean)
    Implementacion:    Mapped[bool | None] = mapped_column(Boolean)
    ImpresionDobleCara:Mapped[bool | None] = mapped_column(Boolean)
    BajoConsumoTinta:  Mapped[bool | None] = mapped_column(Boolean)

    RevisionPoliticaAmbiental: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    FormatoDocumento:          Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    Destruccion:               Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    Donacion:                  Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    Reparacion:                Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    TotalColaboradoresCapacitados: Mapped[int | None]   = mapped_column(Integer)
    TotalColaboradoresConcientizados: Mapped[float | None] = mapped_column(Float)

    FuncionariosDesignados:    Mapped[str | None] = mapped_column(Text)
    FuncionariosDesignadosNum: Mapped[int]        = mapped_column(Integer, nullable=False, default=0)

    EtapaSEV_docs: Mapped[int | None] = mapped_column(Integer)
    ElaboraPolitica:  Mapped[bool | None] = mapped_column(Boolean)
    ActualizaPolitica:Mapped[bool | None] = mapped_column(Boolean)
    MantienePolitica: Mapped[bool | None] = mapped_column(Boolean)

    E1O1RT2:                 Mapped[bool | None] = mapped_column(Boolean)
    DefinicionesEstrategicas:Mapped[bool | None] = mapped_column(Boolean)
    Consultiva:              Mapped[bool | None] = mapped_column(Boolean)
    PorcentajeConcientizadosEtapa2: Mapped[float | None] = mapped_column(Float)
    PorcentajeCapacitadosEtapa2:    Mapped[float | None] = mapped_column(Float)
    PropuestaPorcentaje:            Mapped[float | None] = mapped_column(Float)

    GestionEnergia: Mapped[bool | None] = mapped_column(Boolean)
    GestionVehiculosTs: Mapped[bool | None] = mapped_column(Boolean)
    TrasladoSustentable: Mapped[bool | None] = mapped_column(Boolean)
    GestionAgua:     Mapped[bool | None] = mapped_column(Boolean)
    GestionResiduosEc: Mapped[bool | None] = mapped_column(Boolean)
    GestionComprasS:   Mapped[bool | None] = mapped_column(Boolean)
    GestionBajaBs:     Mapped[bool | None] = mapped_column(Boolean)
    HuellaC:           Mapped[bool | None] = mapped_column(Boolean)
    CambioClimatico:   Mapped[bool | None] = mapped_column(Boolean)
    OtraMateria:       Mapped[bool | None] = mapped_column(Boolean)
    ConsultaPersonal:  Mapped[bool | None] = mapped_column(Boolean)
    DefinePolitica:    Mapped[str | None]  = mapped_column(Text)
    ActividadesCI:     Mapped[bool | None] = mapped_column(Boolean)
    PropuestaTemasCI:  Mapped[str | None]  = mapped_column(Text)

    @declared_attr.directive
    def __mapper_args__(cls):
        if cls.__name__ == "Documento":
            return {
                "polymorphic_on": cls.Discriminator,
                "polymorphic_identity": "Documento",
            }
        return {"polymorphic_identity": cls.__name__}

# ---------- Subtipos (polimorfismo) ----------
class ActaComite(Documento): pass
class Reunion(Documento): pass
class ListaIntegrante(Documento): pass
class Politica(Documento): pass
class DifusionPolitica(Documento): pass
class ProcedimientoPapel(Documento): pass
class ProcedimientoResiduo(Documento): pass
class ProcedimientoResiduoSistema(Documento): pass
class ProcedimientoBajaBienes(Documento): pass
class ProcedimientoCompraSustentable(Documento): pass
class ProcReutilizacionPapel(Documento): pass
class Charla(Documento):
    NParticipantes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
class ListadoColaborador(Documento): pass
class CapacitadosMP(Documento): pass
class GestionCompraSustentable(Documento): pass
class PacE3(Documento): pass
class InformeDA(Documento): pass
class ResolucionApruebaPlan(Documento): pass
