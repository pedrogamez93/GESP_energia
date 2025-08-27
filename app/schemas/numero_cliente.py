from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class NumeroClienteListDTO(BaseModel):
    Id: int
    Numero: Optional[str] = None
    NombreCliente: Optional[str] = None
    EmpresaDistribuidoraId: Optional[int] = None
    TipoTarifaId: Optional[int] = None
    DivisionId: Optional[int] = None
    PotenciaSuministrada: float = 0.0
    Active: bool = True
    class Config: from_attributes = True

class NumeroClienteDTO(NumeroClienteListDTO):
    CreatedAt: Optional[str] = None
    UpdatedAt: Optional[str] = None
    Version: Optional[int] = None

class NumeroClienteCreate(BaseModel):
    Numero: Optional[str] = None
    NombreCliente: Optional[str] = None
    EmpresaDistribuidoraId: Optional[int] = None
    TipoTarifaId: Optional[int] = None
    DivisionId: Optional[int] = None
    PotenciaSuministrada: float = 0.0

class NumeroClienteUpdate(BaseModel):
    Numero: Optional[str] = None
    NombreCliente: Optional[str] = None
    EmpresaDistribuidoraId: Optional[int] = None
    TipoTarifaId: Optional[int] = None
    DivisionId: Optional[int] = None
    PotenciaSuministrada: Optional[float] = None
    Active: Optional[bool] = None
