from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# Elemento para combos
class EmpresaDistribuidoraSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# Item de listado
class EmpresaDistribuidoraDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    RUT: Optional[str] = None
    EnergeticoId: int
    Active: bool = True
    model_config = ConfigDict(from_attributes=True)

# Detalle (incluye comunas)
class EmpresaDistribuidoraDetailDTO(EmpresaDistribuidoraDTO):
    ComunaIds: List[int] = []

# Envoltura de paginación
class EmpresaDistribuidoraListDTO(BaseModel):
    total: int
    data: List[EmpresaDistribuidoraDTO]

# Payloads de escritura
class EmpresaDistribuidoraCreate(BaseModel):
    Nombre: Optional[str] = None
    RUT: Optional[str] = None
    EnergeticoId: int
    ComunaIds: List[int] = []

class EmpresaDistribuidoraUpdate(BaseModel):
    Nombre: Optional[str] = None
    RUT: Optional[str] = None
    EnergeticoId: Optional[int] = None
    Active: Optional[bool] = None
    ComunaIds: Optional[List[int]] = None

# Relación N:M (si se expone)
class EmpresaDistribuidoraComunaDTO(BaseModel):
    Id: int
    EmpresaDistribuidoraId: int
    ComunaId: int
    Active: bool = True
    model_config = ConfigDict(from_attributes=True)
