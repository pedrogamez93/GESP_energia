from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List

# ----- Detalle por medidor -----
class CompraMedidorItemDTO(BaseModel):
    Id: int
    Consumo: float
    MedidorId: int
    ParametroMedicionId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None
    class Config: from_attributes = True

class CompraMedidorItemCreate(BaseModel):
    Consumo: float
    MedidorId: int
    ParametroMedicionId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None

# ----- Compra (cabecera) -----
class CompraListDTO(BaseModel):
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
    class Config: from_attributes = True

class CompraDTO(CompraListDTO):
    UnidadMedidaId: Optional[int] = None
    Observacion: Optional[str] = None
    FacturaId: int
    EstadoValidacionId: Optional[str] = None
    RevisadoPor: Optional[str] = None
    ReviewedAt: Optional[str] = None
    CreatedByDivisionId: int
    ObservacionRevision: Optional[str] = None
    SinMedidor: bool = False

    Items: List[CompraMedidorItemDTO] = Field(default_factory=list)

class CompraCreate(BaseModel):
    Consumo: float
    InicioLectura: str
    FinLectura: str
    DivisionId: int
    EnergeticoId: int
    FechaCompra: str
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
    InicioLectura: Optional[str] = None
    FinLectura: Optional[str] = None
    DivisionId: Optional[int] = None
    EnergeticoId: Optional[int] = None
    FechaCompra: Optional[str] = None
    Costo: Optional[float] = None
    FacturaId: Optional[int] = None

    NumeroClienteId: Optional[int] = None
    UnidadMedidaId: Optional[int] = None
    Observacion: Optional[str] = None
    EstadoValidacionId: Optional[str] = None
    RevisadoPor: Optional[str] = None
    ReviewedAt: Optional[str] = None
    CreatedByDivisionId: Optional[int] = None
    ObservacionRevision: Optional[str] = None
    SinMedidor: Optional[bool] = None

# ----- Payload para reemplazar los items por medidor -----
class CompraItemsPayload(BaseModel):
    Items: List[CompraMedidorItemCreate] = Field(default_factory=list)
