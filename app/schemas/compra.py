# app/schemas/compra.py
from __future__ import annotations

from typing import Optional, List, Union
from datetime import datetime, date, time

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
    field_serializer,
    model_validator,
)

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
    """
    DTO del Medidor:
    - Mantiene tus 4 campos tipados (para que Swagger los muestre),
    - pero permite EXTRA fields (todas las columnas reales de dbo.Medidores).
    """
    model_config = ConfigDict(from_attributes=True, extra="allow")

    Numero: Optional[str] = None
    DeviceId: Optional[int | str] = None
    TipoMedidorId: Optional[int] = None
    Active: Optional[bool] = None


class CompraMedidorItemDTO(BaseModel):
    """Item “básico” (sin anidar el Medidor). Útil en listados y creaciones simples."""
    model_config = ConfigDict(from_attributes=True)

    Id: int
    Consumo: float
    MedidorId: Optional[int] = None
    ParametroMedicionId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None


class CompraMedidorItemFullDTO(CompraMedidorItemDTO):
    """Item enriquecido (detalle): incluye el objeto Medidor."""
    Medidor: Optional[MedidorDTO] = None


class CompraMedidorItemCreate(BaseModel):
    """Payload de creación/edición de items."""
    Consumo: float
    MedidorId: Optional[int] = None
    ParametroMedicionId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("Consumo")
    @classmethod
    def _consumo_pos(cls, v: float):
        if v is None or float(v) < 0:
            raise ValueError("Consumo (item) debe ser ≥ 0")
        return float(v)

    @field_validator("MedidorId", "ParametroMedicionId", "UnidadMedidaId")
    @classmethod
    def _ints_ok(cls, v):
        if v is None:
            return None
        iv = int(v)
        if iv <= 0:
            raise ValueError("Ids de item deben ser enteros positivos")
        return iv


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
    CreatedAt: DateLike = None
    UpdatedAt: DateLike = None
    Consumo: float
    Costo: float
    Active: bool = True

    CreatedBy: Optional[str] = None
    ModifiedBy: Optional[str] = None

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
class CompraCreate(BaseModel):
    """
    Para crear: aceptamos string/date/datetime y normalizamos a datetime,
    pero al serializar de vuelta (si aplica) emitimos string.

    Reglas fuertes:
      - Consumo y Costo ≥ 0.
      - InicioLectura ≤ FinLectura.
      - Si existen todas, FechaCompra ∈ [InicioLectura, FinLectura].
      - Si SinMedidor=false → debe haber Items y todos con MedidorId.
      - Si SinMedidor=true  → no debe venir MedidorId en Items.
      - Suma de Consumo de Items == Consumo total (si hay Items).
      - 🔴 FacturaId es OBLIGATORIO (>0).  ← evita IntegrityError en SQL Server

    ✅ NUEVO:
      - UnidadId (alias opcional): si viene, el backend resolverá DivisionId
        vía UnidadesInmuebles (InmuebleId) en el router/service.
    """
    Consumo: float
    InicioLectura: DateLike
    FinLectura: DateLike

    # ✅ NUEVO (alias opcional)
    UnidadId: Optional[int] = None

    DivisionId: int
    EnergeticoId: int
    FechaCompra: DateLike
    Costo: float

    # mantenemos Optional para no romper firmas previas, pero validamos que sea requerido
    FacturaId: Optional[int] = None
    NumeroClienteId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None
    Observacion: Optional[str] = Field(default=None, max_length=1000)
    EstadoValidacionId: Optional[str] = "sin_revision"
    CreatedByDivisionId: Optional[int] = None
    SinMedidor: bool = False
    Items: List[CompraMedidorItemCreate] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    # ---- Normalización de entrada de fechas ----
    @field_validator("FechaCompra", "InicioLectura", "FinLectura", mode="before")
    @classmethod
    def _coerce_dates(cls, v):
        return _to_datetime(v)

    # ---- Serialización de salida de fechas ----
    @field_serializer("FechaCompra", "InicioLectura", "FinLectura", when_used="json")
    def _ser_dates(self, v: Optional[datetime], _info):
        return _ser_date(v)

    # ---- Validadores de números base ----
    @field_validator("Consumo")
    @classmethod
    def _consumo_total_pos(cls, v: float):
        if v is None or float(v) < 0:
            raise ValueError("Consumo total debe ser ≥ 0")
        return float(v)

    @field_validator("Costo")
    @classmethod
    def _costo_pos(cls, v: float):
        if v is None or float(v) < 0:
            raise ValueError("Costo debe ser ≥ 0")
        return float(v)

    @field_validator(
        "UnidadId",
        "DivisionId", "EnergeticoId", "CreatedByDivisionId", "FacturaId",
        "NumeroClienteId", "UnidadMedidaId", mode="before"
    )
    @classmethod
    def _ints_ok(cls, v):
        if v is None or v == "":
            return None
        iv = int(v)
        if iv <= 0:
            raise ValueError("Ids deben ser enteros positivos")
        return iv

    # ---- Chequeos cruzados (negocio) ----
    @model_validator(mode="after")
    def _cross_checks(self):
        # 1) CreatedByDivisionId por defecto = DivisionId
        # (nota: si usas UnidadId, el router/service puede sobreescribir DivisionId
        #  antes de persistir; aquí mantenemos tu contrato sin romper)
        if self.CreatedByDivisionId is None:
            object.__setattr__(self, "CreatedByDivisionId", self.DivisionId)

        # 2) Rango de lecturas coherente
        if self.InicioLectura and self.FinLectura:
            if self.InicioLectura > self.FinLectura:
                raise ValueError("InicioLectura no puede ser mayor que FinLectura")

        # 3) FechaCompra dentro del rango si existen las tres fechas
        if self.FechaCompra and self.InicioLectura and self.FinLectura:
            if not (self.InicioLectura <= self.FechaCompra <= self.FinLectura):
                raise ValueError("FechaCompra debe caer dentro del rango de lectura")

        # 4) Reglas de Items vs SinMedidor
        if self.SinMedidor:
            if any(it.MedidorId is not None for it in self.Items):
                raise ValueError("SinMedidor=true: no debe enviarse MedidorId en Items")
        else:
            if len(self.Items) == 0:
                raise ValueError("Debe incluir al menos un Item cuando SinMedidor=false")
            if any(it.MedidorId is None for it in self.Items):
                raise ValueError("Todos los Items deben incluir MedidorId cuando SinMedidor=false")

        # 5) Suma de Items = Consumo total (si hay Items)
        if self.Items:
            suma_items = sum(float(it.Consumo or 0) for it in self.Items)
            if abs(float(self.Consumo) - suma_items) > 1e-6:
                raise ValueError("La suma de Consumo en Items debe igualar el Consumo total")

        # 6) 🔴 FacturaId requerido (>0)
        if self.FacturaId is None or int(self.FacturaId) <= 0:
            raise ValueError("FacturaId es obligatorio y debe ser > 0")

        return self


class CompraUpdate(BaseModel):
    """
    Patch/put: mismos criterios; no rompemos llamados existentes.

    ✅ NUEVO:
      - UnidadId (alias opcional): si viene, el backend resolverá DivisionId
        (y puede setear DivisionId internamente).
    """
    Consumo: Optional[float] = None
    InicioLectura: Optional[DateLike] = None
    FinLectura: Optional[DateLike] = None

    # ✅ NUEVO (alias opcional)
    UnidadId: Optional[int] = None

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

    @field_validator("UnidadId", mode="before")
    @classmethod
    def _unidad_int_ok(cls, v):
        if v is None or v == "":
            return None
        iv = int(v)
        if iv <= 0:
            raise ValueError("UnidadId debe ser entero positivo")
        return iv


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

    CreatedBy: Optional[str] = None
    ModifiedBy: Optional[str] = None

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
