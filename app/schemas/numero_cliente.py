from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


# --------- Dirección enriquecida ----------
class DireccionDTO(BaseModel):
    DireccionLibre: Optional[str] = None
    Calle: Optional[str] = None
    Numero: Optional[str] = None
    ComunaId: Optional[int] = None
    ComunaNombre: Optional[str] = None
    RegionId: Optional[int] = None
    RegionNombre: Optional[str] = None


# --------- Listado básico ----------
class NumeroClienteListDTO(BaseModel):
    Id: int
    Numero: Optional[str] = None
    NombreCliente: Optional[str] = None
    EmpresaDistribuidoraId: Optional[int] = None
    TipoTarifaId: Optional[int] = None
    DivisionId: Optional[int] = None
    PotenciaSuministrada: Optional[float] = None
    Active: bool = True

    class Config:
        from_attributes = True  # ORM mode


class NumeroClienteDTO(NumeroClienteListDTO):
    CreatedAt: Optional[datetime] = None   # <- datetime para evitar ResponseValidationError
    UpdatedAt: Optional[datetime] = None
    Version: Optional[int] = None


class NumeroClienteCreate(BaseModel):
    Numero: Optional[str] = None
    NombreCliente: str
    EmpresaDistribuidoraId: int
    TipoTarifaId: int
    DivisionId: Optional[int] = None
    PotenciaSuministrada: Optional[float] = 0.0


class NumeroClienteUpdate(BaseModel):
    Numero: Optional[str] = None
    NombreCliente: Optional[str] = None
    EmpresaDistribuidoraId: Optional[int] = None
    TipoTarifaId: Optional[int] = None
    DivisionId: Optional[int] = None
    PotenciaSuministrada: Optional[float] = None
    Active: Optional[bool] = None


# --------- Paginación ----------
class NumeroClientePage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[NumeroClienteListDTO]

    class Config:
        from_attributes = True


# --------- Detalle enriquecido ----------
class NumeroClienteDetalleDTO(NumeroClienteDTO):
    ServicioId: Optional[int] = None
    ServicioNombre: Optional[str] = None
    InstitucionId: Optional[int] = None
    EdificioId: Optional[int] = None
    RegionId: Optional[int] = None
    Direccion: Optional[DireccionDTO] = None
