from datetime import datetime
from sqlalchemy import BigInteger, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Servicio(Base):
    __tablename__ = "Servicios"
    __table_args__ = {"schema": "dbo"}

    # PK
    Id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Metadatos/estado
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    Version:   Mapped[int]      = mapped_column(BigInteger, nullable=False)
    Active:    Mapped[bool]     = mapped_column(Boolean, nullable=False)

    ModifiedBy: Mapped[str | None] = mapped_column(Text)  # nvarchar(max)
    CreatedBy:  Mapped[str | None] = mapped_column(Text)  # nvarchar(max)

    # Datos de dominio
    Identificador: Mapped[str | None] = mapped_column(Text)  # nvarchar(max)
    InstitucionId: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dbo.Instituciones.Id", ondelete="CASCADE"),
        nullable=False
    )
    Nombre:       Mapped[str | None] = mapped_column(Text)   # nvarchar(max)
    ReportaPMG:   Mapped[bool]       = mapped_column(Boolean, nullable=False)
    OldId:        Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    CompraActiva: Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    GEV3:         Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)

    Justificacion: Mapped[str | None] = mapped_column(Text)  # nvarchar(max)
    RevisionRed:   Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)

    NoDeclaraViajeAvion:               Mapped[bool | None] = mapped_column(Boolean)
    NoRegistraActividadInterna:        Mapped[bool | None] = mapped_column(Boolean)
    NoRegistraDifusionInterna:         Mapped[bool | None] = mapped_column(Boolean)
    NoRegistraDocResiduosCertificados: Mapped[bool | None] = mapped_column(Boolean)
    NoRegistraDocResiduosSistemas:     Mapped[bool | None] = mapped_column(Boolean)
    NoRegistraPoliticaAmbiental:       Mapped[bool | None] = mapped_column(Boolean)
    NoRegistraProcBajaBienesMuebles:   Mapped[bool | None] = mapped_column(Boolean)
    NoRegistraProcComprasSustentables: Mapped[bool | None] = mapped_column(Boolean)
    NoRegistraProcFormalPapel:         Mapped[bool | None] = mapped_column(Boolean)
    NoRegistraReutilizacionPapel:      Mapped[bool | None] = mapped_column(Boolean)

    ComentarioRed: Mapped[str | None] = mapped_column(Text)  # nvarchar(max)

    RevisionDiagnosticoAmbiental: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ColaboradoresModAlcance:      Mapped[int]  = mapped_column(Integer, nullable=False, default=0)
    ModificacioAlcance:           Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    EtapaSEV:                     Mapped[int]  = mapped_column(Integer, nullable=False, default=0)
    BloqueoIngresoInfo:           Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    NoDeclaraViajeAvion2025: Mapped[bool | None] = mapped_column(Boolean)
    PgaObservacionRed:       Mapped[str | None]  = mapped_column(Text)  # nvarchar(max)
    PgaRespuestaRed:         Mapped[str | None]  = mapped_column(Text)  # nvarchar(max)
    PgaRevisionRed:          Mapped[bool | None] = mapped_column(Boolean)

    ValidacionConcientizacion: Mapped[bool | None] = mapped_column(Boolean)
