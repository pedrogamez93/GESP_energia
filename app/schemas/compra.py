# app/schemas/compras.py
from __future__ import annotations

from typing import Optional, List, Union
from datetime import datetime, date, time

from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de fechas (Pydantic v2)
# ─────────────────────────────────────────────────────────────────────────────
DateLike = Union[str, datetime, date, None]


def _to_datetime(v: DateLike) -> Optional[datetime]:
    """Normaliza str/date/datetime/None a datetime (o None) sin lanzar excepciones."""
    if v is None or v == "" or v == "null":
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, time.min)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        # ISO completo
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            # Solo 'YYYY-MM-DD'
            try:
                return datetime.strptime(s[:10], "%Y-%m-%d")
            except Exception:
                return None
    return None


def _ser_date(v: Optional[datetime]) -> Optional[str]:
    """Serializa datetime -> 'YYYY-MM-DD' o None (contrato actual del front)."""
    if v is None:
        return None
    return v.strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# Items de CompraMedidor
# ─────────────────────────────────────────────────────────────────────────────
class MedidorDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Numero: Optional[str] = None
    DeviceId: Optional[int | str] = None
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
    Mantiene fechas como string al serializar (contrato actual del front),
    pero acepta datetime/date/string al validar.
    """
    model_config = ConfigDict(from_attributes=True)

    Id: int
    DivisionId: int
    EnergeticoId: int
    EnergeticoNombre: Optional[str] = None
    NumeroClienteId: Optional[int] = None

    # Aceptan datetime|date|str al ENTRAR, emiten str al SALIR
    FechaCompra: DateLike = None
    InicioLectura: DateLike = None
    FinLectura: DateLike = None

    Consumo: float
    Costo: float
    Active: bool = True

    # Campos aplanados adicionales
    ServicioId: Optional[int] = None
    ServicioNombre: Optional[str] = None

    # ---- Normalización de entrada ----
    @field_validator("FechaCompra", "InicioLectura", "FinLectura", mode="before")
    @classmethod
    def _coerce_dates(cls, v):
        return _to_datetime(v)

    # ---- Serialización de salida (JSON) ----
    @field_serializer("FechaCompra", "InicioLectura", "FinLectura", when_used="json")
    def _ser_dates(self, v: Optional[datetime], _info):
        return _ser_date(v)


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
    Detalle base de una compra (sin contexto).
    Hereda validadores/serializadores de fechas de CompraListDTO.
    """
    model_config = ConfigDict(from_attributes=True)

    UnidadMedidaId: Optional[int] = None
    Observacion: Optional[str] = None
    FacturaId: Optional[int] = None
    EstadoValidacionId: Optional[str] = None
    RevisadoPor: Optional[str] = None

    ReviewedAt: DateLike = None  # misma idea: acepta variantes, serializa str
    CreatedByDivisionId: int
    ObservacionRevision: Optional[str] = None
    SinMedidor: bool = False

    # Items básicos por defecto (en Full sobrescribimos a versión "Full")
    Items: List[CompraMedidorItemDTO] = Field(default_factory=list)

    # Normalizador + serializador para ReviewedAt
    @field_validator("ReviewedAt", mode="before")
    @classmethod
    def _coerce_reviewed(cls, v):
        return _to_datetime(v)

    @field_serializer("ReviewedAt", when_used="json")
    def _ser_reviewed(self, v: Optional[datetime], _info):
        return _ser_date(v)


class CompraContextoDTO(BaseModel):
    """
    Aplanado de contexto que el service anexa (Servicio, Institución, Región, etc.).
    """
    model_config = ConfigDict(from_attributes=True)

    # Servicio / Institución
    ServicioId: Optional[int] = None
    ServicioNombre: Optional[str] = None
    InstitucionId: Optional[int] = None
    InstitucionNombre: str | None = None

    # División enriquecida
    RegionId: Optional[int] = None
    EdificioId: Optional[int] = None
    NombreOpcional: Optional[str] = None
    UnidadReportaPMG: Optional[bool] = None  # el service entrega bool

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
    Sobrescribe Items para usar la versión “Full”.
    """
    Items: List[CompraMedidorItemFullDTO] = Field(default_factory=list)
    EnergeticoNombre: Optional[str] = None


class CompraFullDetalleDTO(CompraFullDTO):
    """
    Detalle enriquecido + Dirección (si existe en tu esquema; si no, vendrá None).
    """
    Direccion: Optional[DireccionDTO] = None


# ─────────────────────────────────────────────────────────────────────────────
# Payloads de creación / edición (escritura)
# ─────────────────────────────────────────────────────────────────────────────
class CompraMedidorItemCreate(BaseModel):
    Consumo: float
    MedidorId: int
    ParametroMedicionId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None


class CompraCreate(BaseModel):
    """
    Para crear: aceptamos string/date/datetime y normalizamos a datetime,
    pero al serializar de vuelta (si aplica) emitimos string.
    """
    Consumo: float
    InicioLectura: DateLike
    FinLectura: DateLike
    DivisionId: int
    EnergeticoId: int
    FechaCompra: DateLike
    Costo: float
    FacturaId: Optional[int] = None
    NumeroClienteId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None
    Observacion: Optional[str] = None
    EstadoValidacionId: Optional[str] = "sin_revision"
    CreatedByDivisionId: Optional[int] = None
    SinMedidor: bool = False
    Items: List[CompraMedidorItemCreate] = Field(default_factory=list)
    
    @field_validator("FechaCompra", "InicioLectura", "FinLectura", mode="before")
    @classmethod
    def _coerce_dates(cls, v):
        return _to_datetime(v)

    @field_serializer("FechaCompra", "InicioLectura", "FinLectura", when_used="json")
    def _ser_dates(self, v: Optional[datetime], _info):
        return _ser_date(v)


class CompraUpdate(BaseModel):
    """
    Patch/put: mismos criterios; no rompemos llamados existentes.
    """
    Consumo: Optional[float] = None
    InicioLectura: Optional[DateLike] = None
    FinLectura: Optional[DateLike] = None
    DivisionId: Optional[int] = None
    EnergeticoId: Optional[int] = None
    FechaCompra: Optional[DateLike] = None
    Costo: Optional[float] = None
    FacturaId: Optional[int] = None
    NumeroClienteId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None
    Observacion: Optional[str] = None
    EstadoValidacionId: Optional[str] = None
    RevisadoPor: Optional[str] = None
    ReviewedAt: Optional[DateLike] = None
    CreatedByDivisionId: Optional[int] = None
    ObservacionRevision: Optional[str] = None
    SinMedidor: Optional[bool] = None

    @field_validator("FechaCompra", "InicioLectura", "FinLectura", "ReviewedAt", mode="before")
    @classmethod
    def _coerce_dates(cls, v):
        return _to_datetime(v)

    @field_serializer("FechaCompra", "InicioLectura", "FinLectura", "ReviewedAt", when_used="json")
    def _ser_dates(self, v: Optional[datetime], _info):
        return _ser_date(v)


class CompraItemsPayload(BaseModel):
    Items: List[CompraMedidorItemCreate] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Listado enriquecido (si lo usas para grids con contexto)
# ─────────────────────────────────────────────────────────────────────────────
class CompraListFullDTO(BaseModel):
    """
    Útil si tu /list devuelve campos enriquecidos en el mismo renglón.
    Mantiene contrato de fechas como string al serializar.
    """
    model_config = ConfigDict(from_attributes=True)

    Id: int
    DivisionId: int
    EnergeticoId: int
    EnergeticoNombre: Optional[str] = None
    NumeroClienteId: Optional[int] = None

    FechaCompra: DateLike = None
    InicioLectura: DateLike = None
    FinLectura: DateLike = None

    Consumo: float
    Costo: float
    Active: bool = True

    # Enriquecidos
    ServicioId: Optional[int] = None
    ServicioNombre: Optional[str] = None
    InstitucionId: Optional[int] = None
    InstitucionNombre: str | None = None
    RegionId: Optional[int] = None
    EdificioId: Optional[int] = None
    NombreOpcional: Optional[str] = None
    UnidadReportaPMG: Optional[bool] = None
    EstadoValidacionId: Optional[str] = None

    MedidorIds: List[int] = Field(default_factory=list)
    PrimerMedidorId: Optional[int] = None

    @field_validator("FechaCompra", "InicioLectura", "FinLectura", mode="before")
    @classmethod
    def _coerce_dates(cls, v):
        return _to_datetime(v)

    @field_serializer("FechaCompra", "InicioLectura", "FinLectura", when_used="json")
    def _ser_dates(self, v: Optional[datetime], _info):
        return _ser_date(v)


class CompraFullPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CompraFullDetalleDTO]
