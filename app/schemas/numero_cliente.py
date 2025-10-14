from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel

# ---- ya existentes (ejemplo) ----
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
        from_attributes = True  # <- importante para ORM

class NumeroClienteDTO(NumeroClienteListDTO):
    CreatedAt: Optional[str] = None
    UpdatedAt: Optional[str] = None
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

# ---- NUEVO: modelo de paginación ----
class NumeroClientePage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[NumeroClienteListDTO]

    class Config:
        from_attributes = True
