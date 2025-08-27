from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class EquipoListDTO(BaseModel):
    Id: int
    Marca: Optional[str] = None
    Modelo: Optional[str] = None
    DivisionId: Optional[int] = None
    TipoTecnologiaId: int
    SistemaId: int
    ModoOperacionId: int
    EnergeticoIn: int
    EnergeticoOut: int
    Active: bool = True

    class Config:
        from_attributes = True

class EquipoDTO(EquipoListDTO):
    CreatedAt: Optional[str] = None
    UpdatedAt: Optional[str] = None
    Version: Optional[int] = None
    AnyoCompra: int
    HorasUso: float
    Potencia: float
    Cantidad: int
    Inversion: int
    CostoMantencion: int
    EnergeticInId: Optional[int] = None
    EnergeticOutId: Optional[int] = None

class EquipoCreate(BaseModel):
    TipoTecnologiaId: int
    SistemaId: int
    ModoOperacionId: int
    EnergeticoIn: int
    EnergeticoOut: int
    DivisionId: Optional[int] = None

    AnyoCompra: int
    HorasUso: float
    Marca: Optional[str] = None
    Modelo: Optional[str] = None
    Potencia: float
    Cantidad: int
    Inversion: int
    CostoMantencion: int

    EnergeticInId: Optional[int] = None
    EnergeticOutId: Optional[int] = None

class EquipoUpdate(BaseModel):
    TipoTecnologiaId: Optional[int] = None
    SistemaId: Optional[int] = None
    ModoOperacionId: Optional[int] = None
    EnergeticoIn: Optional[int] = None
    EnergeticoOut: Optional[int] = None
    DivisionId: Optional[int] = None

    AnyoCompra: Optional[int] = None
    HorasUso: Optional[float] = None
    Marca: Optional[str] = None
    Modelo: Optional[str] = None
    Potencia: Optional[float] = None
    Cantidad: Optional[int] = None
    Inversion: Optional[int] = None
    CostoMantencion: Optional[int] = None

    EnergeticInId: Optional[int] = None
    EnergeticOutId: Optional[int] = None
    Active: Optional[bool] = None
