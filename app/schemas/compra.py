from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class CompraMedidorItemDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: int
    Consumo: float
    MedidorId: int
    ParametroMedicionId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None


class CompraMedidorItemCreate(BaseModel):
    Consumo: float
    MedidorId: int
    ParametroMedicionId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None


class CompraListDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: int
    DivisionId: int
    EnergeticoId: int
    NumeroClienteId: Optional[int] = None
    FechaCompra: datetime
    Consumo: float
    Costo: float
    InicioLectura: datetime
    FinLectura: datetime
    Active: bool = True


class CompraDTO(CompraListDTO):
    model_config = ConfigDict(from_attributes=True)
    UnidadMedidaId: Optional[int] = None
    Observacion: Optional[str] = None
    FacturaId: int
    EstadoValidacionId: Optional[str] = None
    RevisadoPor: Optional[str] = None
    ReviewedAt: Optional[datetime] = None
    CreatedByDivisionId: int
    ObservacionRevision: Optional[str] = None
    SinMedidor: bool = False
    Items: List[CompraMedidorItemDTO] = Field(default_factory=list)


class CompraCreate(BaseModel):
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


class CompraPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CompraListDTO]

class CompraListFullDTO(BaseModel):
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
    UnidadReportaPMG: Optional[int] = None  # 0/1 en origen
    EstadoValidacionId: Optional[str] = None

    # Puede haber varios medidores; devuelvo ambos formatos:
    MedidorIds: List[int] = Field(default_factory=list)
    PrimerMedidorId: Optional[int] = None


class CompraFullPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CompraListFullDTO]

    # --- CONTEXTO PARA DETALLE ENRIQUECIDO (AÑADIR) ---
class CompraContextoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # Servicio / Institución (DimensionServicios -> Servicios)
    ServicioId: Optional[int] = None
    ServicioNombre: Optional[str] = None
    InstitucionId: Optional[int] = None

    # División enriquecida
    RegionId: Optional[int] = None
    EdificioId: Optional[int] = None
    NombreOpcional: Optional[str] = None
    UnidadReportaPMG: Optional[int] = None  # respeta tu tipo actual (0/1)

    # Medidores asociados a la compra
    MedidorIds: List[int] = Field(default_factory=list)
    PrimerMedidorId: Optional[int] = None


class CompraFullDTO(CompraDTO, CompraContextoDTO):
    """Detalle por ID enriquecido: CompraDTO + contexto jerárquico."""
    pass