from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional

class SerieMensualDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Anio: int
    Mes: int
    Consumo: float
    Costo: float

class ConsumoMedidorDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    MedidorId: int
    Numero: Optional[str] = None
    NumeroClienteId: Optional[int] = None
    Consumo: float
    Costo: float

class ConsumoNumeroClienteDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    NumeroClienteId: int
    NumeroCliente: Optional[str] = None
    Consumo: float
    Costo: float

class KPIsDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ConsumoTotal: float
    CostoTotal: float
    CostoUnitario: float
