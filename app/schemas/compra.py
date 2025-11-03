# app/schemas/compras.py
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# Items de CompraMedidor
# ─────────────────────────────────────────────────────────────────────────────
class MedidorDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Numero: Optional[str] = None
    DeviceId: Optional[str] = None
    TipoMedidorId: Optional[int] = None
    Active: Optional[bool] = None


class CompraMedidorItemDTO(BaseModel):
    """Item “básico” (sin anidar el Medidor). Útil en listados y creaciones simples."""
    model_config = ConfigDict(from_attributes=True)
    Id: int
    Consumo: float
    MedidorId: int
    ParametroMedicionId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None


class CompraMedidorItemFullDTO(CompraMedidorItemDTO):
    """Item enriquecido (detalle): incluye el objeto Medidor."""
    Medidor: Optional[MedidorDTO] = None


class CompraMedidorItemCreate(BaseModel):
    """Payload de creación/edición de items."""
    Consumo: float
    MedidorId: int
    ParametroMedicionId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# Listados (lectura)
# ─────────────────────────────────────────────────────────────────────────────
class CompraListDTO(BaseModel):
    """
    Listado básico (lo que devuelve tu service.list()).
    OJO: las fechas vienen como string ISO (por _fmt_dt), no datetime.
    """
    model_config = ConfigDict(from_attributes=True)
    Id: int
    DivisionId: int
    EnergeticoId: int
    NumeroClienteId: Optional[int] = None
    FechaCompra: str
    Consumo: float
    Costo: float
    InicioLectura: str
    FinLectura: str
    Active: bool = True

    # Campos que tú a veces agregas en el aplanado del response
    ServicioId: Optional[int] = None
    ServicioNombre: Optional[str] = None


class CompraPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CompraListDTO]


# ─────────────────────────────────────────────────────────────────────────────
# Detalle base (lectura) + contexto enriquecido
# ─────────────────────────────────────────────────────────────────────────────
class CompraDTO(CompraListDTO):
    """
    Detalle base de una compra (sin contexto). Mantengo fechas como str (lectura).
    """
    model_config = ConfigDict(from_attributes=True)
    UnidadMedidaId: Optional[int] = None
    Observacion: Optional[str] = None
    FacturaId: int
    EstadoValidacionId: Optional[str] = None
    RevisadoPor: Optional[str] = None
    ReviewedAt: Optional[str] = None  # si quisieras datetime, cambia también en el service
    CreatedByDivisionId: int
    ObservacionRevision: Optional[str] = None
    SinMedidor: bool = False
    # Para el detalle enriquecido, sobreescribimos Items más abajo
    Items: List[CompraMedidorItemDTO] = Field(default_factory=list)


class CompraContextoDTO(BaseModel):
    """
    Aplanado de contexto que tu service anexa (Servicio, Institución, Región, etc.).
    """
    model_config = ConfigDict(from_attributes=True)

    # Servicio / Institución
    ServicioId: Optional[int] = None
    ServicioNombre: Optional[str] = None
    InstitucionId: Optional[int] = None

    # División enriquecida
    RegionId: Optional[int] = None
    EdificioId: Optional[int] = None
    NombreOpcional: Optional[str] = None
    UnidadReportaPMG: Optional[bool] = None  # tu service entrega bool

    # Medidores asociados (resumen)
    MedidorIds: List[int] = Field(default_factory=list)
    PrimerMedidorId: Optional[int] = None


class DireccionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Calle: Optional[str] = None
    Numero: Optional[str] = None
    DireccionLibre: Optional[str] = None
    ComunaId: Optional[int] = None
    ComunaNombre: Optional[str] = None
    RegionId: Optional[int] = None
    RegionNombre: Optional[str] = None


class CompraFullDTO(CompraDTO, CompraContextoDTO):
    """
    Detalle enriquecido: Compra base + contexto + Items con Medidor.
    Sobrescribimos Items para usar la versión “Full”.
    """
    Items: List[CompraMedidorItemFullDTO] = Field(default_factory=list)


class CompraFullDetalleDTO(CompraFullDTO):
    """
    Detalle enriquecido + Dirección (si existe en tu esquema; si no, vendrá None).
    """
    Direccion: Optional[DireccionDTO] = None


# ─────────────────────────────────────────────────────────────────────────────
# Payloads de creación / edición (escritura)
# ─────────────────────────────────────────────────────────────────────────────
class CompraCreate(BaseModel):
    """
    Para crear: acá SÍ usamos datetime, porque es lo que envías desde el front.
    """
    Consumo: float
    InicioLectura: datetime
    FinLectura: datetime
    DivisionId: int
    EnergeticoId: int
    FechaCompra: datetime
    Costo: float
    FacturaId: int
    NumeroClienteId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None
    Observacion: Optional[str] = None
    EstadoValidacionId: Optional[str] = "sin_revision"
    CreatedByDivisionId: Optional[int] = None
    SinMedidor: bool = False
    Items: List[CompraMedidorItemCreate] = Field(default_factory=list)


class CompraUpdate(BaseModel):
    """
    Patch/put de campos. Mantén datetime aquí (escritura).
    """
    Consumo: Optional[float] = None
    InicioLectura: Optional[datetime] = None
    FinLectura: Optional[datetime] = None
    DivisionId: Optional[int] = None
    EnergeticoId: Optional[int] = None
    FechaCompra: Optional[datetime] = None
    Costo: Optional[float] = None
    FacturaId: Optional[int] = None
    NumeroClienteId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None
    Observacion: Optional[str] = None
    EstadoValidacionId: Optional[str] = None
    RevisadoPor: Optional[str] = None
    ReviewedAt: Optional[datetime] = None
    CreatedByDivisionId: Optional[int] = None
    ObservacionRevision: Optional[str] = None
    SinMedidor: Optional[bool] = None


class CompraItemsPayload(BaseModel):
    Items: List[CompraMedidorItemCreate] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Listado enriquecido (si lo usas para grids con contexto)
# ─────────────────────────────────────────────────────────────────────────────
class CompraListFullDTO(BaseModel):
    """
    Útil si tu /list devuelve campos enriquecidos en el mismo renglón.
    """
    model_config = ConfigDict(from_attributes=True)
    Id: int
    DivisionId: int
    EnergeticoId: int
    NumeroClienteId: Optional[int] = None
    FechaCompra: str
    Consumo: float
    Costo: float
    InicioLectura: str
    FinLectura: str
    Active: bool = True

    # Enriquecidos
    ServicioId: Optional[int] = None
    ServicioNombre: Optional[str] = None
    InstitucionId: Optional[int] = None
    RegionId: Optional[int] = None
    EdificioId: Optional[int] = None
    NombreOpcional: Optional[str] = None
    UnidadReportaPMG: Optional[bool] = None
    EstadoValidacionId: Optional[str] = None

    MedidorIds: List[int] = Field(default_factory=list)
    PrimerMedidorId: Optional[int] = None


class CompraFullPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CompraListFullDTO]
