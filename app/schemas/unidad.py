from __future__ import annotations
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict

# --------------------------
# DTOs base (ajusta campos)
# --------------------------

class UnidadListDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: int
    Nombre: Optional[str] = None
    # agrega los campos que realmente uses

class UnidadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: int
    Nombre: Optional[str] = None
    # agrega campos de detalle

class UnidadFilterDTO(BaseModel):
    Unidad: Optional[str] = None
    userId: Optional[str] = None
    InstitucionId: Optional[int] = None
    ServicioId: Optional[int] = None
    RegionId: Optional[int] = None

class UnidadPatchDTO(BaseModel):
    # sólo lo que se pueda parchar
    Nombre: Optional[str] = None

# --------------------------
# Page genérico (v2)
# --------------------------
T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    data: List[T]
    total: int
    page: int
    page_size: int
