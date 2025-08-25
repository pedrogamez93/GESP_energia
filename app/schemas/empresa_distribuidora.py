from pydantic import BaseModel
from typing import Optional, List

class EmpresaDistribuidoraSelectDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    class Config: from_attributes = True

class EmpresaDistribuidoraDTO(BaseModel):
    Id: int
    Nombre: Optional[str] = None
    RUT: Optional[str] = None
    EnergeticoId: int
    Active: bool = True
    class Config: from_attributes = True

class EmpresaDistribuidoraDetailDTO(EmpresaDistribuidoraDTO):
    ComunaIds: List[int] = []  # para edición/vista detallada

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
    ComunaIds: Optional[List[int]] = None  # si viene, reemplaza la asignación

# N:M (por si expones endpoints específicos de la relación)
class EmpresaDistribuidoraComunaDTO(BaseModel):
    Id: int
    EmpresaDistribuidoraId: int
    ComunaId: int
    Active: bool = True
    class Config: from_attributes = True
